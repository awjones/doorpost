# Your own private copy

Doorpost is public. Your home setup has things that should never be public:
your web address, your home IP addresses, your family's names, sign-in
settings, and maybe pictures of places only your family cares about.

The `local/` folder is where those go. It sits next to the code, git
ignores it, and Doorpost reads it before its own files. You keep the public
code as it is, add your `local/` folder, and your home keeps working when
you update.

You only need this if you keep your own copy of the code (a "private fork").
If you install Doorpost and set everything up in Settings, you don't need
`local/` at all: your settings live in the data folder, not in the code.

## What goes in local/

```
local/
  config/frame.yaml      your starting settings (read before config/frame.yaml)
  config/chores.yaml     your chores (read before config/chores.yaml)
  .env                   secrets for an install that is not the Home Assistant add-on
  packs/<id>/            your own art packs (see docs/art-packs.md)
  themes/<name>/         your own looks
  web/                   files that replace Doorpost's own, by path:
    img/monogram.png       your family monogram, for example
  addon/addon.conf       the add-on's name, sidebar title and version start
  addon/icon.png         your own add-on icon
  addon/logo.png         your own add-on logo
  scripts/               your own helper scripts (push to your server, and so on)
  denylist.txt           words that must never go public (see below)
  denylist-allow.txt     hits that are on purpose
```

Every part is optional. `local.example/` in the code has samples to copy.

Some rules:

- **Settings saved in Settings win.** `local/config/frame.yaml` is only the
  starting point, the same as `config/frame.yaml`. Once you save a page in
  Settings, the saved value is used.
- **Demo mode ignores `local/config`.** Demo mode always shows the sample
  family. Your art packs and your `local/web` files still show in demo mode,
  so you can check them without your real data.
- **To test with another folder**, set `FRAME_LOCAL_DIR=/path/to/folder`.
  The tests use an empty folder, so your `local/` never changes a test.

## The Home Assistant add-on

`scripts/build-addon.sh` copies `local/config`, `local/packs`,
`local/themes` and `local/web` into the add-on, plus your icon and logo. It
never copies `local/.env`, `local/scripts` or the denylist.

`local/addon/addon.conf` is plain `KEY=value` lines:

```
ADDON_NAME=Our Frame
ADDON_PANEL_TITLE=Our Frame
ADDON_VERSION_PREFIX=1.1
```

Home Assistant offers an update only when the version number goes up. The
version is the prefix plus the number of commits. If you move an existing
install to a copy with fewer commits, raise the prefix (for example to 2.0)
so the new build counts as newer.

Keep the add-on's folder name `family_frame`. Home Assistant knows an add-on
by that name, so the update keeps its data.

## Updating from an older version

The first time the new version starts on data saved by an older one, it
upgrades the data once:

- It keeps a copy of your settings as `settings.before-upgrade.json`.
- It copies the Google sign-in file to its new name, `google.json`. The old
  file stays, so the older version still finds it if you go back.
- It installs the optional art packs, because older versions had all of
  their pictures built in. You can turn them off in Settings > Art packs.

Everything else is read as it is: settings, chores, the screen time log,
lists, photos and focal points, special-day pictures, profile photos and
frame profiles.

To see what it will do before you update, run this on a copy of your data:

```bash
.venv/bin/python -m app.compat /path/to/a/copy/of/data
```

It changes nothing. It also lists title words whose picture no pack has.

## Keeping private words out of the public code

Two tools check for the words in `local/denylist.txt`. Put your family name,
your domain, your home IP addresses, your emails and your Cloudflare Access
IDs in it, one per line.

**Check the whole copy:**

```bash
scripts/check-private.sh
```

It looks in every file outside `local/` (and in file names), ignoring case.
It prints each hit and exits with an error if there is one.

**Check before every push:** turn on the hook once per copy:

```bash
git config core.hooksPath .githooks
```

Before a push to a public remote, it refuses:

- any file under `local/`, in the pushed files or in any outgoing commit;
- any denylist word in the pushed files, in the commit messages, or in any
  version of any file in the outgoing commits (an old version that you
  later fixed still counts, because git keeps it).

A remote counts as public when it is named `public` or `upstream`, when its
address contains `doorpost`, or when you list it:

```bash
git config --add privacy.publicRemote github.com/yourname/doorpost
```

Pushes to your private remote are not checked, because `local/` belongs
there.

If a hit is on purpose (your name in the license file, say), add it to
`local/denylist-allow.txt` as `path: text`.

## A private repo that follows the public one

1. Clone Doorpost into your private repo and add your `local/` folder.
   Commit it there. It is ignored in the public repo, so in your private
   repo add it with `git add -f local`.
2. Make the public repo fetch-only, so a push to it can't happen by
   accident:

   ```bash
   git remote add upstream https://github.com/<owner>/doorpost.git
   git remote set-url --push upstream DISABLED
   ```

3. To update: `git fetch upstream && git merge upstream/main`, run the
   tests, and build the add-on as usual.
4. To give a change back: copy only the public files onto a clean branch of
   the public repo, run `scripts/check-private.sh`, and open a pull request.
   The hook checks it again on the way out.
