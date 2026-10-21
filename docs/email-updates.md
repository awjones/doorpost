# Email updates

Short emails to parents about chores and screen time (Settings > Email updates). The module
is on by default and sends nothing until a sending account and at least one email address
are saved.

## The three emails

| Email | When | What it says |
|---|---|---|
| Daily chore recap | Every day at a set time (7:30 PM by default) | Chores waiting to be checked, what was approved and by whom, what wasn't done, and the weekend so far. Sent before noon it covers yesterday; from noon on, today. Skipped on a day nobody marked or approved a chore. |
| Weekend screen time | One day a week (Friday 4 PM by default) | Saturday and Sunday, a line per kid for setting each device (a "just for" extra goes on Saturday), how it added up, who earned it, and a warning about chores still waiting. Optionally a short update Saturday 8 AM if the total changed. |
| New week reminder | The reminder time on the Screen time page | Sent only when nobody has started a new week yet, with last week's total. |

Each email goes out once per day or week it covers (`email_log` in the database). If the
server was off at send time, it goes out when the server is back, up to two hours late
(the reminder: up to a day). A failed send is tried three times, five minutes apart.

## Quick approve

With **Quick approve from the email** on, each parent's daily recap has an **Approve**
button per waiting chore and an **Approve all** button. No PIN or sign-in is needed: the
link's secret is the permission.

- Each person's email has its own link; only a hash of it is stored (`email_links`).
- A link works for 48 hours. Each chore can be approved once; Undo works for 10 minutes.
- The approval is logged as "<name> (email)".
- Only parents with a PIN get the buttons. Anyone else added on the page (a grandparent, a
  sitter) gets the emails without them.
- Opening a link approves nothing. Mail services open links on their own to check them, so
  the page at `/e/<secret>` approves with a POST from its script. One chore's button
  approves as soon as the page loads; **Approve all** asks once to confirm.

If the frame's address for people is behind a sign-in such as Cloudflare Access, the link
opens that sign-in first unless `/e/*` and `/api/email/*` are let through.

## Approving later in the week

A chore a kid marked done but nobody approved by midnight stays approvable, on the parent
page and from the email, until a new screen time week starts. It counts toward the week
it is approved in.

## Sending account

Settings > Email updates > Sending account. For Gmail or Google Workspace, turn on 2-Step
Verification and make an app password (Google Account > Security > App passwords); a
normal password is refused. Outlook, iCloud Mail and any other SMTP service work too. The
password is kept with the other secrets in the settings store and is never sent back to
the browser.

Demo mode never sends: emails go to an outbox shown on the Settings page.
