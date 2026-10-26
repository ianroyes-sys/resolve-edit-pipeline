import AppKit
import CoreGraphics

let args = CommandLine.arguments
if args.count == 1 || args[1] == "windows" {
    let windows = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as? [[String: Any]] ?? []
    for window in windows where (window[kCGWindowOwnerName as String] as? String ?? "").localizedCaseInsensitiveContains("resolve") {
        print(window)
    }
} else if args[1] == "activate" {
    for app in NSWorkspace.shared.runningApplications where (app.localizedName ?? "").localizedCaseInsensitiveContains("resolve") {
        print(app.activate(options: [.activateIgnoringOtherApps]))
    }
}
