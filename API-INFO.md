# Current target API version

At the moment, the current target API version is 1.8.0

## System

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `ping`                   | Done   |                                          |
| `getLicense`             | Done   |                                          |

## Browsing

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `getMusicFolders`        | Done   |                                          |
| `getIndexes`             | Done   |                                          |
| `getMusicDirectory`      | Done   |                                          |
| `getGenres`              | N/A    | From API v1.9.0                          |
| `getArtists`             | Done   |                                          |
| `getArtist`              | Done   |                                          |
| `getAlbum`               | Done   |                                          |
| `getSong`                | Done   |                                          |
| `getVideos`              | Done   | Not planned, returns an error            |

## Album/song lists

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `getAlbumList`           | Done   |                                          |
| `getAlbumList2`          | Done   |                                          |
| `getRandomSongs`         | Done   |                                          |
| `getSongsByGenre`        | N/A    | From API v1.9.0                          |
| `getNowPlaying`          | Done   |                                          |
| `getStarred`             | Done   |                                          |
| `getStarred2`            | Done   |                                          |

## Searching

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `search`                 | Done   |                                          |
| `search2`                | Done   |                                          |
| `search3`                | Done   |                                          |

## Playlists

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `getPlaylists`           | Done   |                                          |
| `getPlaylist`            | Done   |                                          |
| `createPlaylist`         | Done   |                                          |
| `updatePlaylist`         | Done   |                                          |
| `deletePlaylist`         | Done   |                                          |

## Media retrieval

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `stream`                 | Done   |                                          |
| `download`               | Done   |                                          |
| `hls`                    | N/A    | Video related stuff, not planned         |
| `getCoverArt`            | Done   |                                          |
| `getLyrics`              | Done   | Use either text files or ChartLyrics API |
| `getAvatar`              | TODO   |                                          |

## Media annotation

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `star`                   | Done   |                                          |
| `unstar`                 | Done   |                                          |
| `setRating`              | Done   |                                          |
| `scrobble`               | Done   |                                          |

## Sharing

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `getShares`              | TODO   |                                          |
| `createShare`            | TODO   |                                          |
| `updateShare`            | TODO   |                                          |
| `deleteShare`            | TODO   |                                          |

## Podcast

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `getPodcasts`            | N/A    | Not planned                              |
| `refreshPodcasts`        | N/A    | From API v1.9.0                          |
| `createPodcastChannel`   | N/A    | From API v1.9.0                          |
| `deletePodcastChannel`   | N/A    | From API v1.9.0                          |
| `deletePodcastEpisode`   | N/A    | From API v1.9.0                          |
| `downloadPodcastEpisode` | N/A    | From API v1.9.0                          |

## Jukebox

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `jukeboxControl`         | N/A    | Not planned                              |

## Internet radio

| API call                   | Status | Comments                               |
|----------------------------|--------|----------------------------------------|
| `getInternetRadioStations` | N/A    | From API v1.9.0                        |

## Chat

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `getChatMessages`        | Done   |                                          |
| `addChatMessage`         | Done   |                                          |

## User management

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `getUser`                | Done   |                                          |
| `getUsers`               | Done   |                                          |
| `createUser`             | Done   |                                          |
| `deleteUser`             | Done   |                                          |
| `changePassword`         | Done   |                                          |

## Bookmarks

| API call                 | Status | Comments                                 |
|--------------------------|--------|------------------------------------------|
| `getBookmarks`           | N/A    | From API v1.9.0                          |
| `createBookmark`         | N/A    | From API v1.9.0                          |
| `deleteBookmark`         | N/A    | From API v1.9.0                          |
