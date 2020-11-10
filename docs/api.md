# API breakdown

This page lists all the API methods and their parameters up to the version
1.16.0 (Subsonic 6.1.2). Here you'll find details about which API features
_Supysonic_ support, plan on supporting, or won't.

At the moment, the current target API version is 1.10.2.

The following information was gathered by _diff_-ing various snapshots of the
[Subsonic API page](http://www.subsonic.org/pages/api.jsp).

- [Methods and parameters listing](#methods-and-parameters-listing)
- [Changes by version](#changes-by-version)

## Methods and parameters listing

Statuses explanation:
- 📅: planned
- ✔️: done
- ❌: done as not supported
- 🔴: won't be implemented
- ❔: not decided yet

The version column specifies the API version which added the related method or
parameter. When no version is given, it means the item was introduced prior to
or with version 1.8.0.

### All methods / pseudo-TOC

| Method                                                      | Vers.  |   |
|-------------------------------------------------------------|--------|---|
| [`ping`](#ping)                                             |        | ✔️ |
| [`getLicense`](#getlicense)                                 |        | ✔️ |
| [`getMusicFolders`](#getmusicfolders)                       |        | ✔️ |
| [`getIndexes`](#getindexes)                                 |        | ✔️ |
| [`getMusicDirectory`](#getmusicdirectory)                   |        | ✔️ |
| [`getGenres`](#getgenres)                                   | 1.9.0  | ✔️ |
| [`getArtists`](#getartists)                                 |        | ✔️ |
| [`getArtist`](#getartist)                                   |        | ✔️ |
| [`getAlbum`](#getalbum)                                     |        | ✔️ |
| [`getSong`](#getsong)                                       |        | ✔️ |
| [`getVideos`](#getvideos)                                   |        | ❌ |
| [`getVideoInfo`](#getvideoinfo)                             | 1.15.0 | 🔴 |
| [`getArtistInfo`](#getartistinfo)                           | 1.11.0 | 📅 |
| [`getArtistInfo2`](#getartistinfo2)                         | 1.11.0 | 📅 |
| [`getAlbumInfo`](#getalbuminfo)                             | 1.14.0 | 📅 |
| [`getAlbumInfo2`](#getalbuminfo2)                           | 1.14.0 | 📅 |
| [`getSimilarSongs`](#getsimilarsongs)                       | 1.11.0 | ❔ |
| [`getSimilarSongs2`](#getsimilarsongs2)                     | 1.11.0 | ❔ |
| [`getTopSongs`](#gettopsongs)                               | 1.13.0 | ❔ |
| [`getAlbumList`](#getalbumlist)                             |        | ✔️ |
| [`getAlbumList2`](#getalbumlist2)                           |        | ✔️ |
| [`getRandomSongs`](#getrandomsongs)                         |        | ✔️ |
| [`getSongsByGenre`](#getsongsbygenre)                       | 1.9.0  | ✔️ |
| [`getNowPlaying`](#getnowplaying)                           |        | ✔️ |
| [`getStarred`](#getstarred)                                 |        | ✔️ |
| [`getStarred2`](#getstarred2)                               |        | ✔️ |
| [`search`](#search)                                         |        | ✔️ |
| [`search2`](#search2)                                       |        | ✔️ |
| [`search3`](#search3)                                       |        | ✔️ |
| [`getPlaylists`](#getplaylists)                             |        | ✔️ |
| [`getPlaylist`](#getplaylist)                               |        | ✔️ |
| [`createPlaylist`](#createplaylist)                         |        | ✔️ |
| [`updatePlaylist`](#updateplaylist)                         |        | ✔️ |
| [`deletePlaylist`](#deleteplaylist)                         |        | ✔️ |
| [`stream`](#stream)                                         |        | ✔️ |
| [`download`](#download)                                     |        | ✔️ |
| [`hls`](#hls)                                               | 1.9.0  | 🔴 |
| [`getCaptions`](#getcaptions)                               | 1.15.0 | 🔴 |
| [`getCoverArt`](#getcoverart)                               |        | ✔️ |
| [`getLyrics`](#getlyrics)                                   |        | ✔️ |
| [`getAvatar`](#getavatar)                                   |        | ❌ |
| [`star`](#star)                                             |        | ✔️ |
| [`unstar`](#unstar)                                         |        | ✔️ |
| [`setRating`](#setrating)                                   |        | ✔️ |
| [`scrobble`](#scrobble)                                     |        | ✔️ |
| [`getShares`](#getshares)                                   |        | ❌ |
| [`createShare`](#createshare)                               |        | ❌ |
| [`updateShare`](#updateshare)                               |        | ❌ |
| [`deleteShare`](#deleteshare)                               |        | ❌ |
| [`getPodcasts`](#getpodcasts)                               |        | ❔ |
| [`getNewestPodcasts`](#getnewestpodcasts)                   | 1.14.0 | ❔ |
| [`refreshPodcasts`](#refreshpodcasts)                       | 1.9.0  | ❔ |
| [`createPodcastChannel`](#createpodcastchannel)             | 1.9.0  | ❔ |
| [`deletePodcastChannel`](#deletepodcastchannel)             | 1.9.0  | ❔ |
| [`deletePodcastEpisode`](#deletepodcastepisode)             | 1.9.0  | ❔ |
| [`downloadPodcastEpisode`](#downloadpodcastepisode)         | 1.9.0  | ❔ |
| [`jukeboxControl`](#jukeboxcontrol)                         |        | ✔️ |
| [`getInternetRadioStations`](#getinternetradiostations)     | 1.9.0  | ✔️ |
| [`createInternetRadioStation`](#createinternetradiostation) | 1.16.0 | ✔️ |
| [`updateInternetRadioStation`](#updateinternetradiostation) | 1.16.0 | ✔️ |
| [`deleteInternetRadioStation`](#deleteinternetradiostation) | 1.16.0 | ✔️ |
| [`getChatMessages`](#getchatmessages)                       |        | ✔️ |
| [`addChatMessage`](#addchatmessage)                         |        | ✔️ |
| [`getUser`](#getuser)                                       |        | ✔️ |
| [`getUsers`](#getusers)                                     | 1.9.0  | ✔️ |
| [`createUser`](#createuser)                                 |        | ✔️ |
| [`updateUser`](#updateuser)                                 | 1.10.2 | ✔️ |
| [`deleteUser`](#deleteuser)                                 |        | ✔️ |
| [`changePassword`](#changepassword)                         |        | ✔️ |
| [`getBookmarks`](#getbookmarks)                             | 1.9.0  | ❔ |
| [`createBookmark`](#createbookmark)                         | 1.9.0  | ❔ |
| [`deleteBookmark`](#deletebookmark)                         | 1.9.0  | ❔ |
| [`getPlayQueue`](#getplayqueue)                             | 1.12.0 | ❔ |
| [`savePlayQueue`](#saveplayqueue)                           | 1.12.0 | ❔ |
| [`getScanStatus`](#getscanstatus)                           | 1.15.0 | 📅 |
| [`startScan`](#startscan)                                   | 1.15.0 | 📅 |

### Global

Parameters used for any request

| P.  | Vers.  |   |
|-----|--------|---|
| `u` |        | ✔️ |
| `p` |        | ✔️ |
| `t` | 1.13.0 | 🔴 |
| `s` | 1.13.0 | 🔴 |
| `v` |        | ✔️ |
| `c` |        | ✔️ |
| `f` |        | ✔️ |

Error codes

| #  | Vers.  |   |
|----|--------|---|
| 0  |        | ✔️ |
| 10 |        | ✔️ |
| 20 |        | ✔️ |
| 30 |        | ✔️ |
| 40 |        | ✔️ |
| 41 | 1.15.0 | 📅 |
| 50 |        | ✔️ |
| 60 |        | ✔️ |
| 70 |        | ✔️ |

### System

#### `ping`
✔️
No parameter

#### `getLicense`
✔️
No parameter

### Browsing

#### `getMusicFolders`
✔️
No parameter

#### `getIndexes`
✔️

| Parameter         | Vers. |   |
|-------------------|-------|---|
| `musicFolderId`   |       | ✔️ |
| `ifModifiedSince` |       | ✔️ |

#### `getMusicDirectory`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |

#### `getGenres`
✔️ 1.9.0
No parameter

#### `getArtists`
✔️

| Parameter       | Vers.  |   |
|-----------------|--------|---|
| `musicFolderId` | 1.14.0 | 📅 |

#### `getArtist`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |

#### `getAlbum`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |

#### `getSong`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |

#### `getVideos`
❌
No parameter

#### `getVideoInfo`
🔴 1.15.0

| Parameter | Vers.  |   |
|-----------|--------|---|
| `id`      | 1.15.0 | 🔴 |

#### `getArtistInfo`
📅 1.11.0

| Parameter           | Vers.  |   |
|---------------------|--------|---|
| `id`                | 1.11.0 | 📅 |
| `count`             | 1.11.0 | 📅 |
| `includeNotPresent` | 1.11.0 | 📅 |

#### `getArtistInfo2`
📅 1.11.0

| Parameter           | Vers.  |   |
|---------------------|--------|---|
| `id`                | 1.11.0 | 📅 |
| `count`             | 1.11.0 | 📅 |
| `includeNotPresent` | 1.11.0 | 📅 |

#### `getAlbumInfo`
📅 1.14.0

| Parameter | Vers.  |   |
|-----------|--------|---|
| `id`      | 1.14.0 | 📅 |

#### `getAlbumInfo2`
📅 1.14.0

| Parameter | Vers.  |   |
|-----------|--------|---|
| `id`      | 1.14.0 | 📅 |

#### `getSimilarSongs`
❔ 1.11.0

| Parameter | Vers.  |   |
|-----------|--------|---|
| `id`      | 1.11.0 | ❔ |
| `count`   | 1.11.0 | ❔ |

#### `getSimilarSongs2`
❔ 1.11.0

| Parameter | Vers.  |   |
|-----------|--------|---|
| `id`      | 1.11.0 | ❔ |
| `count`   | 1.11.0 | ❔ |

#### `getTopSongs`
❔ 1.13.0

| Parameter | Vers.  |   |
|-----------|--------|---|
| `artist`  | 1.13.0 | ❔ |
| `count`   | 1.13.0 | ❔ |

### Album/song lists

#### `getAlbumList`
✔️

| Parameter       | Vers.  |   |
|-----------------|--------|---|
| `type`          |        | ✔️ |
| `size`          |        | ✔️ |
| `offset`        |        | ✔️ |
| `fromYear`      |        | ✔️ |
| `toYear`        |        | ✔️ |
| `genre`         |        | ✔️ |
| `musicFolderId` | 1.12.0 | 📅 |

On 1.10.1, `byYear` and `byGenre` were added to `type`

#### `getAlbumList2`
✔️

| Parameter       | Vers.  |   |
|-----------------|--------|---|
| `type`          |        | ✔️ |
| `size`          |        | ✔️ |
| `offset`        |        | ✔️ |
| `fromYear`      |        | ✔️ |
| `toYear`        |        | ✔️ |
| `genre`         |        | ✔️ |
| `musicFolderId` | 1.12.0 | 📅 |

On 1.10.1, `byYear` and `byGenre` were added to `type`

#### `getRandomSongs`
✔️

| Parameter       | Vers. |   |
|-----------------|-------|---|
| `size`          |       | ✔️ |
| `genre`         |       | ✔️ |
| `fromYear`      |       | ✔️ |
| `toYear`        |       | ✔️ |
| `musicFolderId` |       | ✔️ |

#### `getSongsByGenre`
✔️ 1.9.0

| Parameter       | Vers.  |   |
|-----------------|--------|---|
| `genre`         | 1.9.0  | ✔️ |
| `count`         | 1.9.0  | ✔️ |
| `offset`        | 1.9.0  | ✔️ |
| `musicFolderId` | 1.12.0 | 📅 |

#### `getNowPlaying`
✔️
No parameter

#### `getStarred`
✔️

| Parameter       | Vers.  |   |
|-----------------|--------|---|
| `musicFolderId` | 1.12.0 | 📅 |

#### `getStarred2`
✔️

| Parameter       | Vers.  |   |
|-----------------|--------|---|
| `musicFolderId` | 1.12.0 | 📅 |

### Searching

#### `search`
✔️

| Parameter   | Vers. |   |
|-------------|-------|---|
| `artist`    |       | ✔️ |
| `album`     |       | ✔️ |
| `title`     |       | ✔️ |
| `any`       |       | ✔️ |
| `count`     |       | ✔️ |
| `offset`    |       | ✔️ |
| `newerThan` |       | ✔️ |

#### `search2`
✔️

| Parameter       | Vers.  |   |
|-----------------|--------|---|
| `query`         |        | ✔️ |
| `artistCount`   |        | ✔️ |
| `artistOffset`  |        | ✔️ |
| `albumCount`    |        | ✔️ |
| `albumOffset`   |        | ✔️ |
| `songCount`     |        | ✔️ |
| `songOffset`    |        | ✔️ |
| `musicFolderId` | 1.12.0 | 📅 |

#### `search3`
✔️

| Parameter       | Vers.  |   |
|-----------------|--------|---|
| `query`         |        | ✔️ |
| `artistCount`   |        | ✔️ |
| `artistOffset`  |        | ✔️ |
| `albumCount`    |        | ✔️ |
| `albumOffset`   |        | ✔️ |
| `songCount`     |        | ✔️ |
| `songOffset`    |        | ✔️ |
| `musicFolderId` | 1.12.0 | 📅 |

### Playlists

#### `getPlaylists`
✔️

| Parameter  | Vers. |   |
|------------|-------|---|
| `username` |       | ✔️ |

#### `getPlaylist`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |

#### `createPlaylist`
✔️

| Parameter    | Vers. |   |
|--------------|-------|---|
| `playlistId` |       | ✔️ |
| `name`       |       | ✔️ |
| `songId`     |       | ✔️ |

#### `updatePlaylist`
✔️

| Parameter           | Vers. |   |
|---------------------|-------|---|
| `playlistId`        |       | ✔️ |
| `name`              |       | ✔️ |
| `comment`           |       | ✔️ |
| `public`            | 1.9.0 | ✔️ |
| `songIdToAdd`       |       | ✔️ |
| `songIndexToRemove` |       | ✔️ |

#### `deletePlaylist`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |

### Media retrieval

#### `stream`
✔️

| Parameter               | Vers.  |   |
|-------------------------|--------|---|
| `id`                    |        | ✔️ |
| `maxBitRate`            |        | ✔️ |
| `format`                |        | ✔️ |
| `timeOffset`            |        | ❌ |
| `size`                  |        | ❌ |
| `estimateContentLength` |        | ✔️ |
| `converted`             | 1.15.0 | 🔴 |

#### `download`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |

#### `hls`
🔴 1.9.0

| Parameter    | Vers.  |   |
|--------------|--------|---|
| `id`         | 1.9.0  | 🔴 |
| `bitRate`    | 1.9.0  | 🔴 |
| `audioTrack` | 1.15.0 | 🔴 |

#### `getCaptions`
🔴 1.15.0

| Parameter   | Vers.  |   |
|-------------|--------|---|
| `id`        | 1.15.0 | 🔴 |
| `format`    | 1.15.0 | 🔴 |

#### `getCoverArt`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |
| `size`    |       | ✔️ |

#### `getLyrics`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `artist`  |       | ✔️ |
| `title`   |       | ✔️ |

#### `getAvatar`
❌

| Parameter  | Vers. |   |
|------------|-------|---|
| `username` |       | ❌ |

### Media annotation

#### `star`
✔️

| Parameter  | Vers. |   |
|------------|-------|---|
| `id`       |       | ✔️ |
| `albumId`  |       | ✔️ |
| `artistId` |       | ✔️ |

#### `unstar`
✔️

| Parameter  | Vers. |   |
|------------|-------|---|
| `id`       |       | ✔️ |
| `albumId`  |       | ✔️ |
| `artistId` |       | ✔️ |

#### `setRating`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ✔️ |
| `rating`  |       | ✔️ |

#### `scrobble`
✔️

| Parameter    | Vers. |   |
|--------------|-------|---|
| `id`         |       | ✔️ |
| `time`       | 1.9.0 | ✔️ |
| `submission` |       | ✔️ |

### Sharing

#### `getShares`
❌
No parameter

#### `createShare`
❌

| Parameter     | Vers. |   |
|---------------|-------|---|
| `id`          |       | ❌ |
| `description` |       | ❌ |
| `expires`     |       | ❌ |

#### `updateShare`
❌

| Parameter     | Vers. |   |
|---------------|-------|---|
| `id`          |       | ❌ |
| `description` |       | ❌ |
| `expires`     |       | ❌ |

#### `deleteShare`
❌

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      |       | ❌ |

### Podcast

#### `getPodcasts`
❔

| Parameter         | Vers. |   |
|-------------------|-------|---|
| `includeEpisodes` | 1.9.0 | ❔ |
| `id`              | 1.9.0 | ❔ |

#### `getNewestPodcasts`
❔ 1.14.0

| Parameter | Vers.  |   |
|-----------|--------|---|
| `count`   | 1.14.0 | ❔ |

#### `refreshPodcasts`
❔ 1.9.0

No parameter

#### `createPodcastChannel`
❔ 1.9.0

| Parameter | Vers. |   |
|-----------|-------|---|
| `url`     | 1.9.0 | ❔ |

#### `deletePodcastChannel`
❔ 1.9.0

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      | 1.9.0 | ❔ |

#### `deletePodcastEpisode`
❔ 1.9.0

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      | 1.9.0 | ❔ |


#### `downloadPodcastEpisode`
❔ 1.9.0

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      | 1.9.0 | ❔ |

### Jukebox

#### `jukeboxControl`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `action`  |       | ✔️ |
| `index`   |       | ✔️ |
| `offset`  |       | ✔️ |
| `id`      |       | ✔️ |
| `gain`    |       | ❌ |

### Internet radio

#### `getInternetRadioStations`
❔ 1.9.0

No parameter

#### `createInternetRadioStation`
❔ 1.16.0

| Parameter     | Vers.  |   |
|---------------|--------|---|
| `streamUrl`   | 1.16.0 | ❔ |
| `name`        | 1.16.0 | ❔ |
| `homepageUrl` | 1.16.0 | ❔ |

#### `updateInternetRadioStation`
❔ 1.16.0

| Parameter     | Vers.  |   |
|---------------|--------|---|
| `id`          | 1.16.0 | ❔ |
| `streamUrl`   | 1.16.0 | ❔ |
| `name`        | 1.16.0 | ❔ |
| `homepageUrl` | 1.16.0 | ❔ |

#### `deleteInternetRadioStation`
❔ 1.16.0

| Parameter | Vers.  |   |
|-----------|--------|---|
| `id`      | 1.16.0 | ❔ |

### Chat

#### `getChatMessages`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `since`   |       | ✔️ |

#### `addChatMessage`
✔️

| Parameter | Vers. |   |
|-----------|-------|---|
| `message` |       | ✔️ |

### User management

#### `getUser`
✔️

| Parameter  | Vers. |   |
|------------|-------|---|
| `username` |       | ✔️ |

#### `getUsers`
✔️ 1.9.0

No parameter

#### `createUser`
✔️

| Parameter             | Vers.  |   |
|-----------------------|--------|---|
| `username`            |        | ✔️ |
| `password`            |        | ✔️ |
| `email`               |        | ✔️ |
| `ldapAuthenticated`   |        |   |
| `adminRole`           |        | ✔️ |
| `settingsRole`        |        |   |
| `streamRole`          |        |   |
| `jukeboxRole`         |        | ✔️ |
| `downloadRole`        |        |   |
| `uploadRole`          |        |   |
| `playlistRole`        |        |   |
| `coverArtRole`        |        |   |
| `commentRole`         |        |   |
| `podcastRole`         |        |   |
| `shareRole`           |        |   |
| `videoConversionRole` | 1.14.0 |   |
| `musicFolderId`       | 1.12.0 | 📅 |

#### `updateUser`
✔️ 1.10.2

| Parameter             | Vers.  |   |
|-----------------------|--------|---|
| `username`            | 1.10.2 | ✔️ |
| `password`            | 1.10.2 | ✔️ |
| `email`               | 1.10.2 | ✔️ |
| `ldapAuthenticated`   | 1.10.2 |   |
| `adminRole`           | 1.10.2 | ✔️ |
| `settingsRole`        | 1.10.2 |   |
| `streamRole`          | 1.10.2 |   |
| `jukeboxRole`         | 1.10.2 | ✔️ |
| `downloadRole`        | 1.10.2 |   |
| `uploadRole`          | 1.10.2 |   |
| `coverArtRole`        | 1.10.2 |   |
| `commentRole`         | 1.10.2 |   |
| `podcastRole`         | 1.10.2 |   |
| `shareRole`           | 1.10.2 |   |
| `videoConversionRole` | 1.14.0 |   |
| `musicFolderId`       | 1.12.0 | 📅 |
| `maxBitRate`          | 1.13.0 | 📅 |

#### `deleteUser`
✔️

| Parameter  | Vers.  |   |
|------------|--------|---|
| `username` |        | ✔️ |

#### `changePassword`
✔️

| Parameter  | Vers.  |   |
|------------|--------|---|
| `username` |        | ✔️ |
| `password` |        | ✔️ |

### Bookmarks

#### `getBookmarks`
❔ 1.9.0
No parameter

#### `createBookmark`
❔ 1.9.0

| Parameter  | Vers. |   |
|------------|-------|---|
| `id`       | 1.9.0 | ❔ |
| `position` | 1.9.0 | ❔ |
| `comment`  | 1.9.0 | ❔ |

#### `deleteBookmark`
❔ 1.9.0

| Parameter | Vers. |   |
|-----------|-------|---|
| `id`      | 1.9.0 | ❔ |

#### `getPlayQueue`
❔ 1.12.0
No parameter

#### `savePlayQueue`
❔ 1.12.0

| Parameter  | Vers.  |   |
|------------|--------|---|
| `id`       | 1.12.0 | ❔ |
| `current`  | 1.12.0 | ❔ |
| `position` | 1.12.0 | ❔ |

### Library scanning

#### `getScanStatus`
📅 1.15.0
No parameter

#### `startScan`
📅 1.15.0
No parameter

## Changes by version

### Version 1.9.0

Added methods:
- `getGenres`
- `getSongsByGenre`
- `hls`
- `refreshPodcasts`
- `createPodcastChannel`
- `deletePodcastChannel`
- `deletePodcastEpisode`
- `downloadPodcastEpisode`
- `getInternetRadioStations`
- `getUsers`
- `getBookmarks`
- `createBookmark`
- `deleteBookmark`

Added method parameters:
- `updatePlaylist`
  - `public`
- `scrobble`
  - `time`
- `getPodcasts`
  - `includeEpisodes`
  - `id`

### Version 1.10.1

Added method parameters:
- `getAlbumList`
  - `fromYear`
  - `toYear`
  - `genre`
- `getAlbumList2`
  - `fromYear`
  - `toYear`
  - `genre`

### Version 1.10.2

Added methods:
- `updateUser`

### Version 1.11.0

Added methods:
- `getArtistInfo`
- `getArtistInfo2`
- `getSimilarSongs`
- `getSimilarSongs2`

### Version 1.12.0

Added methods:
- `getPlayQueue`
- `savePlayQueue`

Added method parameters:
- `getAlbumList`
  - `musicFolderId`
- `getAlbumList2`
  - `musicFolderId`
- `getSongsByGenre`
  - `musicFolderId`
- `getStarred`
  - `musicFolderId`
- `getStarred2`
  - `musicFolderId`
- `search2`
  - `musicFolderId`
- `search3`
  - `musicFolderId`
- `createUser`
  - `musicFolderId`
- `updateUser`
  - `musicFolderId`

### Version 1.13.0

Added global parameters:
- `t`
- `s`

Added methods:
- `getTopSongs`

Added method parameters:
- `updateUser`
  - `maxBitRate`

### Version 1.14.0

Added methods:
- `getAlbumInfo`
- `getAlbumInfo2`
- `getNewestPodcasts`

Added method parameters:
- `getArtists`
  - `musicFolderId`
- `createUser`
  - `videoConversionRole`
- `updateUser`
  - `videoConversionRole`

### Version 1.15.0

Added error code `41`

Added methods:
- `getVideoInfo`
- `getCaptions`
- `getScanStatus`
- `startScan`

Added method parameters:
- `stream`
  - `converted`
- `hls`
  - `audioTrack`

### Version 1.16.0

Added methods:
- `createInternetRadioStation`
- `updateInternetRadioStation`
- `deleteInternetRadioStation`

