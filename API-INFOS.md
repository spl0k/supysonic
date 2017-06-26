# Current target API version

At the moment, the current target API version is 1.8.0

<table>
  <tr><th>Module</th><th>API call</th><th>Status</th><th>Comments</th></tr>

  <tr><th rowspan="2">System</th>	<td>ping</td>	<td style="background-color: green">Done</td>	<td></td></tr>
  <tr>	<td>getLicense</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="9">Browsing</th>	<td>getMusicFolders</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getIndexes</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getMusicDirectory</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getGenres</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>getArtists</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getArtist</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getAlbum</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getSong</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getVideos</td>	<td>Done</td>	<td>Actually returns an error as video support is not planned</td></tr>

  <tr><th rowspan="7">Album/song lists</th>	<td>getAlbumList</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getAlbumList2</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getRandomSongs</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getSongsByGenre</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>getNowPlaying</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getStarred</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getStarred2</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="3">Searching</th>	<td>search</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>search2</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>search3</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="5">Playlists</th>	<td>getPlaylists</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getPlaylist</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>createPlaylist</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>updatePlaylist</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>deletePlaylist</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="6">Media retrieval</th>	<td>stream</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>download</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>hls</td>	<td>N/A</td>	<td>Video related stuff, not planned</td></tr>
  <tr>	<td>getCoverArt</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getLyrics</td>	<td>Done</td>	<td>Use either text files or ChartLyrics API</td></tr>
  <tr>	<td>getAvatar</td>	<td><strong>TODO</strong></td>	<td>Not that useful for a streaming server, but whatever</td></tr>

  <tr><th rowspan="4">Media annotation</th>	<td>star</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>unstar</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>setRating</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>scrobble</td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="4">Sharing</th>	<td>getShares</td>	<td><strong>TODO</strong></td>	<td rowspan="4">Need to look how this works on the official Subsonic server</td></tr>
  <tr>	<td>createShare</td>	<td><strong>TODO</strong></td></tr>
  <tr>	<td>updateShare</td>	<td><strong>TODO</strong></td></tr>
  <tr>	<td>deleteShare</td>	<td><strong>TODO</strong></td></tr>

  <tr><th rowspan="6">Podcast</th>	<td>getPodcasts</td>	<td>N/A</td>	<td>Not planning to support podcasts at the moment</td></tr>
  <tr>	<td>refreshPodcasts</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>createPodcastChannel</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>deletePodcastChannel</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>deletePodcastEpisode</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>downloadPodcastEpisode</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>

  <tr><th>Jukebox</th>	<td>jukeboxControl</td>	<td>N/A</td>	<td>Not planning to support the Jukebox feature</td></tr>

  <tr><th>Internet radio</th>	<td>getInternetRadioStations </td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>

  <tr><th rowspan="2">Chat</th>	<td>getChatMessages</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>addChatMessage </td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="5">User management</th>	<td>getUser</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>getUsers</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>createUser</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>deleteUser</td>	<td>Done</td>	<td></td></tr>
  <tr>	<td>changePassword </td>	<td>Done</td>	<td></td></tr>

  <tr><th rowspan="3">Bookmarks</th>	<td>getBookmarks</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>createBookmark</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
  <tr>	<td>deleteBookmark</td>	<td>N/A</td>	<td>From API v1.9.0</td></tr>
</table>
