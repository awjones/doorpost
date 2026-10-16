// Doorpost Lists: passes Apple Reminders lists to the Doorpost and back (see docs/lists.md).
// launchd runs it every 30 seconds on the Mac; each run is one check-in, then it exits.
// It sends only the lists chosen in Settings > Lists (plus the names of the others, so they can be picked),
// and writes to Reminders whatever was added or checked off on the frame.
import EventKit
import Foundation

let env = ProcessInfo.processInfo.environment
let frameURL = env["FRAME_URL"] ?? "http://doorpost.local:8090"
let tokenService = env["FRAME_TOKEN_SERVICE"] ?? "Doorpost upload token"   // the Keychain item (mac/install-lists-helper.sh)
let home = FileManager.default.homeDirectoryForCurrentUser
let stateDir = home.appendingPathComponent("Library/Application Support/FamilyFrame")
let wantFile = stateDir.appendingPathComponent("lists-want.json")
let iso = ISO8601DateFormatter()

func log(_ s: String) {
    let line = "\(iso.string(from: Date())) \(s)\n"
    FileHandle.standardError.write(line.data(using: .utf8)!)
}

// The upload key lives in the login Keychain (the same one the Favorites sync uses).
func uploadToken() -> String? {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: "/usr/bin/security")
    p.arguments = ["find-generic-password", "-s", tokenService, "-a", "frame", "-w"]
    let out = Pipe()
    p.standardOutput = out
    p.standardError = Pipe()
    do { try p.run() } catch { return nil }
    p.waitUntilExit()
    guard p.terminationStatus == 0 else { return nil }
    let s = String(data: out.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8)?
        .trimmingCharacters(in: .whitespacesAndNewlines)
    return (s?.isEmpty ?? true) ? nil : s
}

let store = EKEventStore()

func requestAccess() -> Bool {
    let sem = DispatchSemaphore(value: 0)
    var ok = false
    if #available(macOS 14.0, *) {
        store.requestFullAccessToReminders { granted, _ in ok = granted; sem.signal() }
    } else {
        store.requestAccess(to: .reminder) { granted, _ in ok = granted; sem.signal() }
    }
    sem.wait()
    return ok
}

func fetch(_ predicate: NSPredicate) -> [EKReminder] {
    let sem = DispatchSemaphore(value: 0)
    var out: [EKReminder] = []
    store.fetchReminders(matching: predicate) { r in out = r ?? []; sem.signal() }
    sem.wait()
    return out
}

func snapshot(want: [String]) -> [String: Any] {
    store.refreshSourcesIfNecessary()
    let cals = store.calendars(for: .reminder)
    let open = fetch(store.predicateForIncompleteReminders(withDueDateStarting: nil, ending: nil, calendars: cals))
    var counts: [String: Int] = [:]
    for r in open { counts[r.calendar.calendarIdentifier, default: 0] += 1 }
    let lists = cals.map { ["id": $0.calendarIdentifier, "name": $0.title, "count": counts[$0.calendarIdentifier] ?? 0] as [String: Any] }
    var items: [String: [[String: Any]]] = [:]
    let wanted = cals.filter { want.contains($0.calendarIdentifier) }
    if !wanted.isEmpty {
        // Open items, plus ones checked off in the last two days (for "Done today").
        let done = fetch(store.predicateForCompletedReminders(withCompletionDateStarting: Date().addingTimeInterval(-2 * 86400),
                                                               ending: Date(), calendars: wanted))
        for c in wanted { items[c.calendarIdentifier] = [] }
        for r in open.filter({ want.contains($0.calendar.calendarIdentifier) }) + done {
            var it: [String: Any] = ["ext": r.calendarItemIdentifier, "title": r.title ?? "", "notes": r.notes ?? "", "done": r.isCompleted]
            if let d = r.completionDate { it["done_at"] = iso.string(from: d) }
            if let d = r.creationDate { it["created"] = iso.string(from: d) }
            if let d = r.lastModifiedDate { it["modified"] = iso.string(from: d) }
            items[r.calendar.calendarIdentifier, default: []].append(it)
        }
    }
    return ["lists": lists, "items": items]
}

func post(_ body: [String: Any], token: String) -> [String: Any]? {
    var req = URLRequest(url: URL(string: frameURL + "/api/lists/sync")!, timeoutInterval: 20)
    req.httpMethod = "POST"
    req.setValue("application/json", forHTTPHeaderField: "Content-Type")
    req.setValue(token, forHTTPHeaderField: "X-Upload-Token")
    req.httpBody = try? JSONSerialization.data(withJSONObject: body)
    let sem = DispatchSemaphore(value: 0)
    var result: [String: Any]?
    URLSession.shared.dataTask(with: req) { data, resp, err in
        if let err = err { log("frame not reachable: \(err.localizedDescription)") }
        else if let h = resp as? HTTPURLResponse, h.statusCode != 200 { log("frame said \(h.statusCode)") }
        else if let data = data { result = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] }
        sem.signal()
    }.resume()
    sem.wait()
    return result
}

// Write the frame's changes into Reminders; report each one back.
func apply(_ changes: [[String: Any]]) -> [[String: Any]] {
    var applied: [[String: Any]] = []
    for ch in changes {
        let local = ch["local"] as? String ?? ""
        do {
            if ch["op"] as? String == "add" {
                guard let cal = store.calendar(withIdentifier: ch["list"] as? String ?? "") else {
                    applied.append(["local": local, "ok": false]); continue
                }
                let r = EKReminder(eventStore: store)
                r.calendar = cal
                r.title = ch["title"] as? String ?? ""
                if let n = ch["notes"] as? String, !n.isEmpty { r.notes = n }
                if ch["done"] as? Bool == true { r.isCompleted = true }
                try store.save(r, commit: true)
                applied.append(["local": local, "ok": true, "ext": r.calendarItemIdentifier])
                log("added \"\(r.title ?? "")\" to \(cal.title)")
            } else {
                guard let r = store.calendarItem(withIdentifier: ch["ext"] as? String ?? "") as? EKReminder else {
                    applied.append(["local": local, "ok": false]); continue
                }
                r.isCompleted = ch["done"] as? Bool ?? true
                try store.save(r, commit: true)
                applied.append(["local": local, "ok": true])
                log("\(r.isCompleted ? "checked off" : "put back") \"\(r.title ?? "")\"")
            }
        } catch {
            log("couldn't write to Reminders: \(error.localizedDescription)")
            applied.append(["local": local, "ok": false])
        }
    }
    return applied
}

guard requestAccess() else {
    log("Reminders access is off. Turn on Doorpost Lists in System Settings > Privacy & Security > Reminders.")
    exit(2)
}
guard let token = uploadToken() else { log("no upload key in the Keychain (\(tokenService))"); exit(3) }
try? FileManager.default.createDirectory(at: stateDir, withIntermediateDirectories: true)
var want = (try? JSONSerialization.jsonObject(with: Data(contentsOf: wantFile))) as? [String] ?? []

guard let r1 = post(snapshot(want: want), token: token) else { exit(1) }
let want2 = r1["want"] as? [String] ?? []
let applied = apply(r1["changes"] as? [[String: Any]] ?? [])
if want2 != want || !applied.isEmpty {
    // Send the lists again right away: newly picked lists, and the items just written with their Reminders ids.
    var body = snapshot(want: want2)
    body["applied"] = applied
    _ = post(body, token: token)
    want = want2
    try? JSONSerialization.data(withJSONObject: want).write(to: wantFile)
}
