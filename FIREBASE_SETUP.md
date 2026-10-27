# Connecting Firebase (free Spark plan)

The game already contains all Firebase code. You only create a project, switch on two free features, paste the security rules, and copy two values into `index.html`. No credit card or billing account is needed, and nothing in this setup uses a paid feature.

What Firebase gives the game:
- **Ranking** (gold, height, rubies, gems, trophies; top 99; player cards) that works everywhere: from a file, GitHub Pages, Firebase Hosting, or any website. Before this it only worked inside claude.ai.
- **Online mode** finds rooms through Firebase instead of the PeerJS server. Players then connect **directly to each other** (WebRTC), so the game traffic does not count against your Firebase quota. If Firebase cannot be reached, the game falls back to PeerJS as before.
- **Sign-in without registration**: each device gets an anonymous Firebase account automatically.

Until both values are filled in, Firebase stays off and the game works exactly as before.

## Steps in the Firebase Console (about 10 minutes, works from a phone browser too)

1. **Create the project**
   1. Open https://console.firebase.google.com and sign in with your Google account.
   2. Click **Create a project** (or **Add project**).
   3. Name it, for example `wall-play`, and click **Continue**.
   4. If you are offered **Gemini in Firebase**, you can leave it off.
   5. **Google Analytics**: switch it **off** (the game doesn't need it). Click **Create project**, wait, then **Continue**.
   6. New projects are on the **Spark** (free) plan. In the bottom-left corner of the console you should see **Spark** / **No-cost**. **Never click "Upgrade"** or link a billing account. Without a billing account, Firebase cannot charge you; when a free limit runs out, that service simply pauses until the limit resets.

2. **Register a web app (to get the API key)**
   1. On the project overview page, click the **Web** icon `</>` (under "Get started by adding Firebase to your app").
   2. App nickname: `Wall Play`. Leave **"Also set up Firebase Hosting"** unticked. Click **Register app**.
   3. You will see a block `const firebaseConfig = { apiKey: "AIza...", ... }`. Copy the value of **apiKey** (the text inside the quotes after `apiKey:`).
   4. Click **Continue to console**. You can find this config again at ⚙ **Project settings → General → Your apps → SDK setup and configuration → Config**.

3. **Turn on anonymous sign-in**
   1. Left menu: **Build → Authentication** → **Get started**.
   2. Open the **Sign-in method** tab → choose **Anonymous** → switch **Enable** on → **Save**.

4. **Create the Realtime Database**
   1. Left menu: **Build → Realtime Database** → **Create Database**.
   2. **Location**: pick the region closest to your players (for Europe: `europe-west1 (Belgium)`; otherwise `us-central1`). Click **Next**.
   3. Choose **Start in locked mode** → **Enable**.
   4. At the top of the **Data** tab you will see the database address, such as `https://wall-play-1234-default-rtdb.europe-west1.firebasedatabase.app` (or `...firebaseio.com`). Copy it **without** a trailing slash.

5. **Paste the security rules** (they protect the ranking and the rooms)
   1. In **Realtime Database**, open the **Rules** tab.
   2. Delete everything in the editor and paste the whole contents of `database.rules.json` from this repository.
   3. Click **Publish**.

6. **Put the two values into the game**
   1. Open `index.html` in a text editor and search for `const FIREBASE = {`.
   2. Fill in the two lines:
      ```js
      apiKey: 'AIza...your key...',
      databaseURL: 'https://wall-play-1234-default-rtdb.europe-west1.firebasedatabase.app',
      ```
   3. Save the file.

7. **Check it**
   - Open the game → **Ranking**: after your first run, you appear in the table.
   - **Online**: create a room on one device and join with the code on another.
   - In the console, **Realtime Database → Data** shows `board`, `profiles` and, while a room is open, `rooms`.

## Optional: free hosting on Firebase (needs a computer with Node.js)

This gives you a link like `https://wall-play-1234.web.app`. It also uploads the rules from `database.rules.json` automatically, so you can skip step 5 in the console.

```bash
cd wall-play
npx firebase-tools login            # opens the browser once
npx firebase-tools use --add        # pick your project, alias: default
npx firebase-tools deploy --only hosting,database
```

## Optional: limit the API key

The `apiKey` is not a secret. It only names your project; the protection comes from the database rules. If you want extra safety:

1. Open https://console.cloud.google.com/apis/credentials and select your project.
2. Open **Browser key (auto created by Firebase)**.
3. Under **API restrictions**, select **Restrict key** and tick **Identity Toolkit API** and **Token Service API**. Then **Save**.

Don't add "HTTP referrer" restrictions if you play the game by opening the file directly, because files have no referrer.

## What the rules enforce (the server-side check of results)

- Each player can write only their own row (`board/<uid>`, `profiles/<uid>`), and nobody can read the database without signing in.
- The height record and trophies cannot grow faster than 60 m per second of server time since the last update. Negative or absurd numbers are rejected, and the time stamp must come from the server.
- Nobody can take over someone else's open room. Room invitations can be read only by the player they are addressed to, and the sender cannot be faked.
- Abandoned rooms can be reused after 2 hours.

Limits: on Spark there are no Cloud Functions, so the game cannot run its own server code. A determined cheater can still post plausible fake numbers, but not impossible ones.

## Free limits that matter (Spark)

| What | Free limit | What uses it in the game |
|---|---|---|
| Realtime Database simultaneous connections | 100 | Each player who is currently in the **Online** room screen or in an online match (one live connection each). The ranking and saves use short requests, not live connections. |
| Realtime Database storage | 1 GB | About 1–8 KB per player (row and profile). |
| Realtime Database download | 10 GB per month | One ranking tab is about 15–25 KB. Online matches send almost nothing through Firebase, because the game data goes directly between players. |
| Anonymous Authentication | free | One account per device or browser. |

If a limit is reached, that feature stops until the limit resets: the ranking shows "No connection", and online mode falls back to PeerJS. You are never billed.

## For development: local emulator (no project needed)

```bash
npx firebase-tools emulators:start --only auth,database --project demo-wallplay
```

Then, in `index.html`, set:
`FIREBASE.apiKey = 'demo'`, `FIREBASE.databaseURL = 'http://127.0.0.1:9000'`, `FIREBASE.emu = { auth: 'http://127.0.0.1:9099', ns: 'demo-wallplay-default-rtdb' }`.

The emulator works only when the page is served without the CSP line, or when `http://127.0.0.1:*` is added to `connect-src`.
