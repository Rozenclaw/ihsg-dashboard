# IHSG Dashboard — Android app (WebView wrapper)

A thin native shell around the dashboard hosted on **Streamlit Community Cloud**.
The app just opens your `https://….streamlit.app` URL in a full-screen WebView
with pull-to-refresh, in-app navigation, and a back button.

**Why a wrapper?** Streamlit is a *server* app. The real dashboard lives in the
cloud, so **updates happen by `git push`** (Community Cloud auto-redeploys) — the
phone shows the new version on next open. You only ever rebuild this APK if the
**URL** changes.

---

## One-time setup

1. Deploy the dashboard to Streamlit Community Cloud first (see `../DEPLOY.md`)
   and copy your public URL, e.g. `https://ihsg-dashboard.streamlit.app`.
2. Open [`app/src/main/res/values/strings.xml`](app/src/main/res/values/strings.xml)
   and replace `https://YOUR-APP-NAME.streamlit.app` with that URL.

## Build the APK (Android Studio — recommended)

1. **Android Studio → Open** → select this `android/` folder.
2. Let Gradle sync finish. If it offers to install/upgrade anything
   (Android Gradle Plugin, SDK 36, build-tools), **accept**.
3. **Build → Build App Bundle(s) / APK(s) → Build APK(s)**.
4. When it finishes, click **locate** → grab
   `app/build/outputs/apk/debug/app-debug.apk`.

## Build from the command line (optional)

```bash
cd android
./gradlew assembleDebug
# -> app/build/outputs/apk/debug/app-debug.apk
```
(Needs a `local.properties` with `sdk.dir=/Users/<you>/Library/Android/sdk`;
Android Studio writes this automatically when you open the project.)

## Install on your phone

- **USB:** enable Developer Options + USB debugging, then
  `adb install -r app/build/outputs/apk/debug/app-debug.apk`.
- **No cable:** copy the `.apk` to the phone (Drive / email / USB storage), tap
  it, and allow "install from unknown sources" when prompted.

The build is **debug-signed**, so it installs without a Play Store account or a
release keystore — perfect for personal use and testing.

---

## What the wrapper handles

- Full-screen WebView, cosmic-dark background to match the dashboard.
- **Pull down to refresh.**
- Back button navigates web history, then exits.
- Links to other sites (news, AI Studio) open in the system browser.
- Report downloads (`.md`) hand off to the browser/Downloads.
- HTTPS-only (`usesCleartextTraffic=false`) — safe for the public URL.

## Updating the dashboard later

You almost never touch this app again. To change the dashboard, edit the Python
and `git push` — Community Cloud redeploys and the app reflects it on next open.
Rebuild the APK **only** if you move it to a different URL.
