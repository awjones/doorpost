import Vision
import CoreImage
import AppKit
// Lift every foreground subject out of an image (the same Vision feature as Photos' "lift subject").
let input = URL(fileURLWithPath: CommandLine.arguments[1])
let outDir = URL(fileURLWithPath: CommandLine.arguments[2])
let handler = VNImageRequestHandler(url: input)
let req = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([req])
guard let res = req.results?.first else { print("no subjects"); exit(1) }
let ctx = CIContext()
print("instances:", res.allInstances.count)
for (n, inst) in res.allInstances.enumerated() {
    let buf = try res.generateMaskedImage(ofInstances: IndexSet(integer: inst), from: handler, croppedToInstancesExtent: true)
    let ci = CIImage(cvPixelBuffer: buf)
    guard let cg = ctx.createCGImage(ci, from: ci.extent) else { continue }
    let rep = NSBitmapImageRep(cgImage: cg)
    let png = rep.representation(using: .png, properties: [:])!
    let url = outDir.appendingPathComponent("subject-\(n).png")
    try png.write(to: url)
    print(url.lastPathComponent, cg.width, "x", cg.height)
}
