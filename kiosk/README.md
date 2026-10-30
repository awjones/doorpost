# Doorpost kiosk

Wes Bos's Home HQ kiosk (`dashboard/kiosk/` in github.com/wesbos/photo-frame-dashboard,
copied at `fbe9a30`) with three changes:

- `DEFAULT_URL` is `http://doorpost.local:8090/`. Change it to your Doorpost server's address
  (in `MainActivity.java`) before you build.
- The main activity is also a **Home** app, so the frame opens it after a power cut.
- The label is "Doorpost".

## License

This folder is not covered by Doorpost's MIT license. It is Wes Bos's code,
included here as he posted it publicly, so it's easy to build alongside the
rest of Doorpost. His repo has no license file, so all rights stay with him.
If you want to reuse this code beyond building your own frame, go to
[his repo](https://github.com/wesbos/photo-frame-dashboard).

Hold two fingers still for 1.5 s for the menu (open launcher, Android settings, reload).

Build (JDK 17 + Android build-tools 34 + platform 34):

```
JAVA_HOME=/opt/homebrew/opt/openjdk@17 PATH=/opt/homebrew/opt/openjdk@17/bin:$PATH bash kiosk/build.sh
adb install -r kiosk/build/homehq.apk
```
