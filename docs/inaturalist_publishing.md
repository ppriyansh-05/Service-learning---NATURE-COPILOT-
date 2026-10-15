# iNaturalist OAuth and approval-gated publishing

Nature Copilot's iNaturalist Upload section now supports this workflow:

1. An NGO administrator unlocks editing in Nature Copilot.
2. They click **Connect iNaturalist** and sign in on iNaturalist's official page.
3. The connected account and status appear in the upload section.
4. The user selects eligible RSWF planted-tree records and reviews the photo, species, date and GPS preview.
5. After clicking **Approve & Upload**, the backend rechecks eligibility and submits the observation and stored photo to iNaturalist.
6. Nature Copilot saves the iNaturalist URL/ID and publishing status in the NGO observation store. Duplicate submissions are blocked.
7. When dashboard data is loaded, an imported iNaturalist row is hidden from dashboard counts/lists only when its explicit iNaturalist observation ID matches a linked NGO planted-tree record. The source CSV, NGO record and remote iNaturalist observation are not deleted.
8. For a linked/published record, **Edit on iNaturalist** opens that observation's edit page in a new tab. Edits there are made on iNaturalist; they do not overwrite the NGO's original planted-tree register or monitoring history.

Only NGO-owned records marked `planted_rswf` with `identification_status` of `verified` or `corrected` can be published. Public iNaturalist reference records and ordinary sightings are excluded. The browser never receives the OAuth client secret or access token.

## Render setup required

The code is committed, but publishing will remain disabled until the following server-side environment variables are configured.

| Variable | Value |
| --- | --- |
| `INATURALIST_CLIENT_ID` | Client ID from the iNaturalist OAuth application |
| `INATURALIST_CLIENT_SECRET` | Client secret from that OAuth application; keep it private |
| `INATURALIST_REDIRECT_URI` | Exact callback URL registered in iNaturalist; for the current backend deployment: `https://van-udyan-backend-byfn.onrender.com/api/v1/inaturalist/oauth/callback` |
| `FRONTEND_PUBLIC_URL` | Public dashboard origin, e.g. `https://van-udyan-dashboard-8dtw.onrender.com` |
| `INATURALIST_TOKEN_ENCRYPTION_KEY` | A new Fernet key generated for this deployment |
| `BACKEND_PUBLIC_URL` | Backend origin, e.g. `https://van-udyan-backend-byfn.onrender.com` (already used elsewhere by the app) |

Register the exact `INATURALIST_REDIRECT_URI` as the OAuth callback/redirect URL in the iNaturalist application settings. Do not add a trailing slash to one side unless it matches the other exactly.

Generate an encryption key locally in a trusted terminal after installing the backend requirements:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the generated value into Render's `INATURALIST_TOKEN_ENCRYPTION_KEY` environment variable. Never commit the generated key, client secret, access token, or any populated `.env` file. Keep the encryption key stable: changing it makes the stored OAuth token unreadable and requires reconnecting the account.

The OAuth token is encrypted before it is saved. In production the encrypted connection is persisted through the configured Postgres `app_state` store; if durable persistence is unavailable, the app will not report a successful connection.

## Operational notes

- The final publish endpoint requires the existing NGO admin password as well as a connected iNaturalist account.
- iNaturalist is the authority for the remote record. If publishing fails, the local queue shows a failed status; fix the reported issue and retry after checking iNaturalist for a record that may already have been created.
- Species names are resolved to an exact iNaturalist taxon match before submission. If no exact match is returned, publishing stops rather than guessing.
- The publish operation includes the uploaded photo, observation date, GPS coordinates, site description and Van Udyan/RSWF tags.
- Duplicate hiding is deliberately based on the linked iNaturalist observation ID/URL, not species name or GPS. Two observations of the same species or at nearby coordinates are not automatically treated as duplicates.
- Editing a published observation on iNaturalist does not update the original NGO register; keep that register as the source of truth for planted-tree identity and monitoring.
- Test first with one approved, non-sensitive planted-tree record. Confirm the photo, taxon, date and coordinates on iNaturalist before using batch approval.
- OAuth/API behavior can change. Confirm account permissions and perform an end-to-end test after deploying and setting the environment variables.

## API routes

- `GET /api/v1/inaturalist/status` — connection status only (never returns a token).
- `POST /api/v1/inaturalist/connect` — NGO-admin-protected OAuth start; returns an authorization URL.
- `GET /api/v1/inaturalist/oauth/callback` — OAuth callback.
- `POST /api/v1/inaturalist/publish/{observation_id}` — NGO-admin-protected, approval-triggered publication.
