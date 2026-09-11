import AppKit
import Security
import Foundation
import CryptoKit
import Darwin

let service = "Blake-PE Mail Accounts"
let mode = CommandLine.arguments.dropFirst().first ?? "setup"
func digest(_ values: [String]) -> String {
    SHA256.hash(data: Data(values.joined(separator: "\0").utf8)).map { String(format: "%02x", $0) }.joined()
}
func query(_ key: String) -> [String: Any] {
    [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: key]
}
if mode == "read" {
    guard CommandLine.arguments.count == 3 else { exit(2) }
    let key = CommandLine.arguments[2]
    guard key.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil else { exit(2) }
    var q = query(key)
    q[kSecReturnData as String] = true
    q[kSecMatchLimit as String] = kSecMatchLimitOne
    var value: CFTypeRef?
    guard SecItemCopyMatching(q as CFDictionary, &value) == errSecSuccess, let bytes = value as? Data else { exit(10) }
    FileHandle.standardOutput.write(bytes)
    exit(0)
}
struct Account: Codable {
    let sender: String
    let display_name: String
    let username: String
    let smtp_host: String
    let smtp_port: Int
    let smtp_security: String
    let imap_host: String
    let imap_port: Int
    var key: String { digest([sender, username, smtp_host, String(smtp_port), smtp_security, imap_host, String(imap_port)]) }
    var valid: Bool {
        let text = [sender, display_name, username, smtp_host, imap_host]
        if text.contains(where: { $0.isEmpty || $0 != $0.trimmingCharacters(in: .whitespacesAndNewlines) || $0.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }) }) { return false }
        guard sender.count <= 254, display_name.count <= 200, username.count <= 254, sender == sender.lowercased(),
              sender.range(of: "^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\\.[A-Za-z]{2,63}$", options: .regularExpression) != nil else { return false }
        let parts = sender.split(separator: "@")
        guard parts.count == 2, !parts[0].hasPrefix("."), !parts[0].hasSuffix("."), !sender.contains("..") else { return false }
        for host in [smtp_host, imap_host] {
            if host.count > 254 || host.contains("..") || host.range(of: "^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$", options: .regularExpression) == nil { return false }
        }
        return (1...65535).contains(smtp_port) && (1...65535).contains(imap_port) && ["ssl", "starttls"].contains(smtp_security)
    }
}
struct Settings: Codable { var accounts: [Account] }
// This mode checks cross-language identity hashing without reading Keychain.
if mode == "validate" {
    guard let account = try? JSONDecoder().decode(Account.self, from: FileHandle.standardInput.readDataToEndOfFile()), account.valid else { exit(2) }
    print(account.key)
    exit(0)
}
guard mode == "setup" else { exit(2) }
let app = NSApplication.shared
app.setActivationPolicy(.accessory)
app.activate(ignoringOtherApps: true)
func fail(_ message: String) -> Never {
    let alert = NSAlert()
    alert.messageText = "Blake-PE setup"
    alert.informativeText = message
    alert.runModal()
    exit(13)
}
let directory = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Blake-PE")
let settingsURL = directory.appendingPathComponent("accounts.json")
func load() throws -> Settings {
    if !FileManager.default.fileExists(atPath: settingsURL.path) { return Settings(accounts: []) }
    let settings = try JSONDecoder().decode(Settings.self, from: Data(contentsOf: settingsURL))
    guard settings.accounts.allSatisfy({ $0.valid }), Set(settings.accounts.map { $0.sender }).count == settings.accounts.count else { throw NSError(domain: "Blake-PE", code: 1) }
    return settings
}
let saved: Settings
do { saved = try load() } catch { fail("Account settings could not be read. No existing settings were replaced.") }
var existing: Account? = nil
if !saved.accounts.isEmpty {
    let chooser = NSAlert()
    chooser.messageText = "Connect or update a mailbox"
    chooser.informativeText = "Choose Add new mailbox, or reconnect one of your accounts. Updating settings requires entering that mailbox password again."
    let menu = NSPopUpButton(frame: NSRect(x: 0, y: 0, width: 470, height: 30))
    menu.addItems(withTitles: ["Add new mailbox"] + saved.accounts.map { $0.sender })
    chooser.accessoryView = menu
    chooser.addButton(withTitle: "Continue")
    chooser.addButton(withTitle: "Cancel")
    guard chooser.runModal() == .alertFirstButtonReturn else { exit(11) }
    if menu.indexOfSelectedItem > 0 { existing = saved.accounts[menu.indexOfSelectedItem - 1] }
}
let alert = NSAlert()
alert.messageText = "Connect your email to Blake-PE"
alert.informativeText = "Defaults are for Namecheap Private Email. For another provider, enter its SMTP/IMAP settings. Use a mailbox or app password, not your provider account password. Credentials will authenticate only to the servers shown below. OAuth sign-in is not supported. No email is sent by setup."
let form = NSView(frame: NSRect(x: 0, y: 0, width: 480, height: 540))
func field(_ title: String, _ value: String, _ row: Int, secure: Bool = false) -> NSTextField {
    let y = 505 - row * 58
    let label = NSTextField(labelWithString: title)
    label.frame = NSRect(x: 0, y: y, width: 480, height: 20)
    let input: NSTextField = secure ? NSSecureTextField() : NSTextField()
    input.frame = NSRect(x: 0, y: y - 27, width: 480, height: 26)
    input.stringValue = value
    form.addSubview(label); form.addSubview(input)
    return input
}
let email = field("Your email address", existing?.sender ?? "", 0)
email.placeholderString = "you@yourdomain.com"
if existing != nil { email.isEditable = false }
let name = field("Sender display name", existing?.display_name ?? "", 1)
let user = field("Login username (leave blank to use your email)", existing?.username ?? "", 2)
let smtp = field("SMTP server", existing?.smtp_host ?? "mail.privateemail.com", 3)
let smtpPort = field("SMTP port (465 for TLS; usually 587 for STARTTLS)", String(existing?.smtp_port ?? 465), 4)
let securityLabel = NSTextField(labelWithString: "SMTP security")
securityLabel.frame = NSRect(x: 0, y: 215, width: 480, height: 20)
let security = NSPopUpButton(frame: NSRect(x: 0, y: 188, width: 480, height: 26))
security.addItems(withTitles: ["SSL/TLS", "STARTTLS"])
security.selectItem(at: existing?.smtp_security == "starttls" ? 1 : 0)
form.addSubview(securityLabel); form.addSubview(security)
let imap = field("IMAP server (SSL/TLS)", existing?.imap_host ?? "mail.privateemail.com", 6)
let imapPort = field("IMAP TLS port", String(existing?.imap_port ?? 993), 7)
let password = field("Mailbox / app password — saved only in macOS Keychain", "", 8, secure: true)
alert.accessoryView = form
alert.addButton(withTitle: "Save & Check Connection")
alert.addButton(withTitle: "Cancel")
alert.window.initialFirstResponder = existing == nil ? email : password
while true {
    guard alert.runModal() == .alertFirstButtonReturn else { exit(11) }
    let trim: (String) -> String = { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
    let sender = trim(email.stringValue).lowercased()
    let profile = Account(sender: sender, display_name: trim(name.stringValue), username: trim(user.stringValue).isEmpty ? sender : trim(user.stringValue), smtp_host: trim(smtp.stringValue).lowercased(), smtp_port: Int(smtpPort.stringValue) ?? 0, smtp_security: security.indexOfSelectedItem == 0 ? "ssl" : "starttls", imap_host: trim(imap.stringValue).lowercased(), imap_port: Int(imapPort.stringValue) ?? 0)
    if !profile.valid || password.stringValue.isEmpty {
        let warning = NSAlert(); warning.messageText = "Check your mailbox details"; warning.informativeText = "Enter a valid email, sender name, server hostnames, numeric ports and password. No account has been saved."; warning.runModal(); continue
    }
    do { try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700]) } catch { fail("Could not create private settings storage.") }
    let lock = open(directory.appendingPathComponent("accounts.lock").path, O_CREAT | O_RDWR, 0o600)
    guard lock >= 0, flock(lock, LOCK_EX) == 0 else { fail("Could not lock settings. Try again.") }
    var current: Settings
    do { current = try load() } catch { fail("Account settings changed or became unreadable. No existing settings were replaced.") }
    var q = query(profile.key)
    let secret = Data(password.stringValue.utf8)
    let updates = [kSecValueData as String: secret]
    var status = SecItemUpdate(q as CFDictionary, updates as CFDictionary)
    if status == errSecItemNotFound {
        q[kSecValueData as String] = secret
        q[kSecAttrLabel as String] = "Blake-PE — \(profile.sender)"
        status = SecItemAdd(q as CFDictionary, nil)
    }
    password.stringValue = ""
    guard status == errSecSuccess else { fail("Keychain could not save the password (code \(status)). Unlock your login Keychain and try again.") }
    current.accounts.removeAll { $0.sender == profile.sender }
    current.accounts.append(profile)
    current.accounts.sort { $0.sender < $1.sender }
    do {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(current).write(to: settingsURL, options: [.atomic, .completeFileProtectionUnlessOpen])
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: settingsURL.path)
    } catch { fail("Password was saved in Keychain, but account settings could not be saved. Reopen setup to finish.") }
    flock(lock, LOCK_UN); close(lock)
    print(profile.sender)
    exit(0)
}
