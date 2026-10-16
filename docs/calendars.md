# Calendars

The frame reads your family's calendars and shows them. It never changes them.
Each calendar is set up in **Settings > Calendars**. Press **Add a calendar from**
and pick where it lives: **Google**, **Apple iCloud**, **Outlook** or **Other link**.
After you paste an address or sign in, press **Check**. It reads the calendar once
and tells you how many events it found in the next two weeks.

Addresses and passwords are kept only on the home computer that runs Doorpost.
They are never sent to the frame or back to your browser. Settings only shows that
one is saved.

You can mix and match. For example, Dad's work calendar from Outlook, Mom's
calendar from iCloud and the family calendar from Google.

## Two ways to connect

| | A link (iCal address) | A private sign-in (CalDAV) |
|---|---|---|
| Works with | Google, Outlook, iCloud public calendars, most calendar apps | Apple iCloud, Fastmail, Nextcloud and other CalDAV services |
| Who can read it | **Anyone who has the link** | Only someone with the password |
| How to stop it | Reset or unpublish the link | Delete the app-specific password |

A link is the simplest. Treat it like a password: don't post it or share it.

## Google

1. Open Google Calendar on a computer. Click the gear, then **Settings**.
2. On the left, under **Settings for my calendars**, click the calendar.
3. Click **Integrate calendar** and copy the **Secret address in iCal format**.
4. Paste it in Settings > Calendars, then press **Check**.

Use the *secret* address, not the *public* one. The public address only works if
the calendar is public to the whole internet. Settings warns you if you paste it.

**Privacy:** anyone with the secret address can read the calendar.
**To revoke:** in the same place in Google Calendar, press **Reset** next to the
secret address. The old one stops working. Paste the new one into Settings.

## Apple iCloud (private, recommended)

This signs in to iCloud with an *app-specific password*. That is a separate
password just for Doorpost. It can only read and write calendars, contacts
and similar data, and it can't be used to change your Apple account.

1. Go to **account.apple.com** and sign in. (Two-factor authentication must be on.
   It usually is.)
2. Open **Sign-In and Security**, then **App-Specific Passwords**. Make one called
   "Doorpost" and copy it. It looks like `abcd-efgh-ijkl-mnop`.
3. In Settings > Calendars, add an **Apple iCloud** calendar. Type your Apple ID
   email and the app-specific password, then press **Find my calendars**.
4. Pick the calendar from the list, then press **Check** and **Save calendars**.

Add one calendar row for each iCloud calendar you want to show. You only type the
password once per row. After that, leave the password box empty to keep the saved
one.

**Privacy:** private. Only the home computer signs in.
**To revoke:** at account.apple.com, open App-Specific Passwords and delete
"Doorpost". The frame keeps showing the last copy it read and marks the
calendar with a problem until you type a new password.

## Apple iCloud (public link)

If you'd rather not use a password, iCloud can share a calendar as a public link.

1. On your iPhone, open **Calendar**, tap **Calendars**, then the **i** next to the
   calendar.
2. Turn on **Public Calendar**, then tap **Share Link** and copy it.
3. In Settings > Calendars, add an **Apple iCloud** calendar and choose **Public link**.
   Paste the link (a `webcal://` link is fine), then press **Check**.

**Privacy:** anyone with the link can read the calendar.
**To revoke:** turn **Public Calendar** off. Turning it back on makes a new link.

## Outlook (Outlook.com and Microsoft 365)

1. Open Outlook on the web. Go to **Settings**, **Calendar**, then **Shared calendars**.
2. Under **Publish a calendar**, pick the calendar and **Can view all details**,
   then press **Publish**.
3. Copy the **ICS** link (not the HTML one). Paste it in Settings > Calendars, then
   press **Check**.

Some work accounts don't allow publishing. If you don't see **Publish a calendar**,
ask whoever runs your work email.

**Privacy:** anyone with the link can read the calendar.
**To revoke:** in the same place, press **Unpublish**. Publishing again makes a new link.

## Other calendars

**A link.** Most calendar apps can publish or export a calendar as an iCal address.
Look for **Publish**, **Share**, **Subscribe** or **Export as iCal**. The address
usually ends in `.ics` or starts with `webcal://`. Add an **Other link** calendar
and paste it.

**A CalDAV account.** For Fastmail, Nextcloud and other CalDAV services, add an
**Other link** calendar and choose **A CalDAV account**. Then type:

- the server address, for example `https://caldav.fastmail.com` or
  `https://cloud.example.com/remote.php/dav`
- your sign-in name
- an app password made in that service's security settings

Press **Find my calendars**, pick one, then **Check**.

## When something goes wrong

- If a calendar can't be read (no internet, a changed password, a reset link),
  the frame keeps showing the last copy it read. Settings shows a red
  **Problem** chip on that calendar with the reason, and the Overview page lists it.
- Calendars are read again every 5 minutes. Tapping the top-left corner of a
  frame reads them right away.
- "Sign-in failed": check the email, and make sure you used the app-specific
  password, not your normal Apple ID password.
- "Not an iCal feed": the address is for a web page, not the calendar file.
  Copy the iCal or ICS address instead.

## For people editing config files

Calendars set in Settings are saved in `data/settings.json` (only readable by the
server's user). You can also list them in `config/frame.yaml`:

```yaml
calendars:
  - key: family
    label: Family
    color: "#9E2235"
    provider: google              # google, icloud, outlook or other (a label for Settings)
    ics_url_env: CAL_FAMILY_ICS   # the address itself goes in .env
  - key: mom
    label: Mom
    color: "#8B4F24"
    provider: icloud
    kind: caldav                  # a private sign-in instead of a link
    caldav_server: https://caldav.icloud.com
    caldav_user: mom@example.com
    caldav_password_env: CAL_MOM_PASSWORD   # the app-specific password goes in .env
    caldav_calendar: https://...  # easiest to pick with Find my calendars in Settings
```

The frame asks a CalDAV server for events from about two months back to a year
ahead, which covers every view.
