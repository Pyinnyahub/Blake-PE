# Blake-PE for Mac — ကိုယ်ပိုင် Email နဲ့ သုံးရန်

**Version 1.0.2 · Public preview · macOS**

Blake-PE က Mac ပေါ်က Codex မှာ ကိုယ်ပိုင် email account တွေ ချိတ်ပြီး စာပို့ခြင်း၊ Inbox ဖတ်ခြင်းနဲ့ ရှာဖွေခြင်းတို့ လုပ်နိုင်တဲ့ plugin ဖြစ်ပါတယ်။ Account အများအပြား ထည့်နိုင်ပြီး စာပို့တိုင်း sender ကို ရွေးနိုင်ပါတယ်။

[Download v1.0.2](https://github.com/Pyinnyahub/Blake-PE/releases/tag/v1.0.2) မှ **Blake-PE-Mac-v1.0.2.zip** ကို ရယူနိုင်ပါတယ်။ GitHub collaborator ဖိတ်ကြားချက် မလိုပါ။

## မစခင် လိုအပ်တာ

- macOS 12 သို့မဟုတ် နောက်ပိုင်း။ Apple Silicon နဲ့ Intel helper နှစ်မျိုး ပါပါတယ်။
- Codex desktop app တင်ထားပြီး login ဝင်ထားရန်။
- Python 3.10 သို့မဟုတ် နောက်ပိုင်း။ မရှိလျှင် [Python for macOS](https://www.python.org/downloads/macos/) မှ install လုပ်ပါ။ Python installer ရဲ့ certificate setup ပါလျှင် အဲဒီညွှန်ကြားချက်ကိုလည်း လိုက်နာပါ။
- ပထမဆုံး install လုပ်ချိန် internet လိုပါတယ်။ Installer က သီးခြား Python runtime တည်ဆောက်ပြီး လိုအပ်တဲ့ MCP package ကို ထည့်ပေးပါတယ်။
- သင့် provider က SMTP/IMAP ကို mailbox password သို့မဟုတ် app password နဲ့ ချိတ်ခွင့်ပေးထားရန်။ **OAuth / Sign in with Google / Microsoft login flow မပါပါ။** SMTP နဲ့ IMAP အတွက် username/password တူညီရပါမယ်။

## ၁ — Install လုပ်ပါ

ZIP ဖိုင်ကို ဖြည်ပြီး **Install Blake-PE.command** ကို ဖွင့်ပါ။ Install အောင်မြင်တဲ့စာ ပြသည်အထိ စောင့်ပါ။

ဒီ community package ကို Apple Developer ID နဲ့ sign/notarize မလုပ်ရသေးပါ။ macOS က unknown developer လို့ ပိတ်ထားပြီး ဒီ package ကို ယုံကြည်စိတ်ချကြောင်း စစ်ထားပြီးဖြစ်လျှင် **System Settings → Privacy & Security → Open Anyway** ရှိမရှိ စစ်ပါ။ အဖွဲ့အစည်းပိုင် Mac ဆိုရင် admin က ခွင့်ပြုချက်လိုနိုင်ပါတယ်။ [Apple ၏ တရားဝင်ညွှန်ကြားချက်](https://support.apple.com/en-ca/102445)

## ၂ — ကိုယ်ပိုင် Mailbox ချိတ်ပါ

**Connect Mailbox.command** ကို ဖွင့်ပြီး အောက်ပါတို့ ဖြည့်ပါ။

| Field | ဖြည့်ရမည့်အရာ |
| --- | --- |
| Your email address | သင့် email အပြည့်အစုံ |
| Sender display name | စာလက်ခံသူမြင်ရမည့် နာမည် |
| Login username | Provider ပေးထားသည့် username; email နဲ့တူရင် အလွတ်ထားနိုင် |
| SMTP server / port / security | Provider ၏ outgoing server setting |
| IMAP server / port | Provider ၏ incoming TLS server setting |
| Mailbox / app password | သင့် mailbox password သို့မဟုတ် app password |

**Save & Check Connection** နှိပ်ပါ။ Password ကို ဒီ Mac ရဲ့ Keychain ထဲမှာ သိမ်းပြီး SMTP/IMAP login စစ်ပေးပါတယ်။ Setup က email မပို့ပါ။ Login မအောင်မြင်လျှင် setup ကို ပြန်ဖွင့်ပြီး setting ပြင်ပါ။

Namecheap Private Email အတွက် မူလဖြည့်ပေးထားတာက SMTP `mail.privateemail.com`, port `465`, SSL/TLS; IMAP `mail.privateemail.com`, port `993` ဖြစ်ပါတယ်။ အခြား provider အတွက် host နဲ့ port ကို သူတို့ညွှန်ကြားချက်အတိုင်း ပြောင်းပါ။ SMTP STARTTLS သုံးလျှင် security ကို STARTTLS ရွေးပြီး port ကိုလည်း provider သတ်မှတ်ချက်အတိုင်း ပြောင်းရပါမယ်။ [Namecheap setup လမ်းညွှန်](https://www.namecheap.com/support/knowledgebase/article.aspx/10781/2175/private-email-account-setup-in-mail-on-macos/)

Account ထပ်ထည့်ချင်ရင် **Connect Mailbox.command → Add new mailbox** ကိုရွေးပါ။ ရှိပြီးသား account ကိုရွေးပြီး ပြန်ချိတ်နိုင်ပါတယ်။ Password ကို chat ထဲမှာ မရေးပါနဲ့။

## ၃ — Codex မှာ သုံးပါ

Task အသစ်ဖွင့်ပြီး **Blake-PE** plugin ကိုရွေးပါ။ ပြီးရင် ဒီလိုပြောနိုင်ပါတယ်—

> Show my connected email accounts.

> Sender list ပြပေး၊ ငါရွေးမယ်။

> ငါရွေးထားတဲ့ account ရဲ့ unread email တွေ ပြပေး။

စာပို့ဖို့ sender၊ လက်ခံသူနဲ့ စာသားကို ပေးပါ။ ပို့မယ့်စာကို အရင်စစ်လိုလျှင် draft ပြင်ပေးရန် တောင်းဆိုပါ။ Sender ကို chat ထဲမှာ email လိပ်စာနဲ့ သတ်မှတ်နိုင်ပါတယ်။ ဥပမာ `hello@example.com ကနေ ပို့ဖို့ draft ပြင်ပေးပါ` လို့ ရေးနိုင်ပါတယ်။ ဒီလိပ်စာက နမူနာသာဖြစ်ပြီး ချိတ်ထားတဲ့ ကိုယ်ပိုင်လိပ်စာနဲ့ အစားထိုးပါ။

## သုံးနိုင်သည့်အရာနှင့် ကန့်သတ်ချက်

- ကိုယ်ပိုင် account များမှ sender ရွေးပြီး plain-text email နဲ့ file attachments ပို့နိုင်ပါတယ်။
- Account တစ်ခုချင်းစီရဲ့ Inbox ကို ဖတ်/ရှာနိုင်ပြီး unread state မပြောင်းပါ။
- “accepted” က mail server လက်ခံခြင်းကို ဆိုလိုပါတယ်။ Gmail/အခြား Inbox ထဲ ရောက်ပြီးကြောင်း အတည်ပြုချက် မဟုတ်ပါ။
- Batch တစ်ခုလျှင် လက်ခံသူ ၅၀၊ attachment ၁၀ ခု၊ encoding မလုပ်မီ စုစုပေါင်း 15 MB အထိ။ Provider ကန့်သတ်ချက်လည်း ရှိနိုင်ပါတယ်။
- IMAP TLS ကိုပဲ support လုပ်ပါတယ်။ IMAP STARTTLS နဲ့ OAuth-only provider များ မပါပါ။
- Sent folder ထဲ အလိုအလျောက် copy သိမ်းခြင်း၊ reply thread ဆက်ပို့ခြင်း၊ background monitor မပါပါ။ Attachment ဖတ်ခြင်းက filename/type/size အချက်အလက်အထိပဲ ဖြစ်ပါတယ်။
- Inbox အချိန်ပြသမှုက Asia/Bangkok ဖြစ်ပါတယ်။ Date filter က IMAP delivery date ကို သုံးပါတယ်။

## ကိုယ်ပိုင် data ဘယ်မှာရှိလဲ

- Account setting၊ draft၊ receipt: `~/Library/Application Support/Blake-PE/`
- Password: macOS Keychain မှ `Blake-PE` အမည်ပါ item များ
- Plugin source: `~/plugins/blake-pe/`

Email ဖတ်ပြီး Codex ကို ပြပေးသောအကြောင်းအရာသည် သင့် Codex conversation ထဲ ပါလာပါတယ်။ Plugin ကို remove လုပ်ခြင်းက settings/drafts/password များကို အလိုအလျောက် မဖျက်ပါ။ Server setting ပြောင်းလျှင် credential အသစ်ချိတ်ပြီး draft အသစ် ပြင်ပါ။ အရင် setting နဲ့ဆိုင်တဲ့ Keychain item ကို လိုအပ်ပါက Keychain Access မှ ဖယ်ရှားနိုင်ပါတယ်။

## စမ်းသပ်ဗားရှင်းအကြောင်းနှင့် အကူအညီ

ဒီဗားရှင်းက public preview ဖြစ်ပါတယ်။ Mac မော်ဒယ်နဲ့ email provider အားလုံးကို လက်တွေ့စမ်းသပ်ထားခြင်း မရှိသေးပါ။ Setup ပြီးလျှင် ကိုယ်တိုင်စစ်နိုင်တဲ့ လိပ်စာတစ်ခုဆီ test email ပို့ပြီး Inbox ဖတ်နိုင်မှုကိုလည်း စစ်ပါ။ စမ်းသပ်ထားသည့်အရာများနဲ့ ကျန်ရှိသည့် ကန့်သတ်ချက်တွေကို [QA status](https://github.com/Pyinnyahub/Blake-PE/blob/main/QA-STATUS.md) မှာ ဖတ်နိုင်ပါတယ်။

အဆင်မပြေမှုတွေကို [GitHub Issues](https://github.com/Pyinnyahub/Blake-PE/issues) မှာ တင်ပြနိုင်ပါတယ်။ macOS version၊ Blake-PE version နဲ့ error စာသားကို ထည့်ပါ။ Password၊ email စာအပြည့်အစုံနဲ့ ကိုယ်ရေးအချက်အလက်တွေကို ဖယ်ရှားပြီးမှ တင်ပါ။
