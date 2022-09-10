Subsonic API breakdown
======================

This page lists all the API methods and their parameters up to the version
1.16.0 (Subsonic 6.1.2). Here you'll find details about which API features
Supysonic support, plan on supporting, or won't.

At the moment, the current target API version is 1.12.0.

The following information was gathered by *diff*-ing various snapshots of the
`Subsonic API page`__.

__ http://www.subsonic.org/pages/api.jsp

Methods and parameters listing
------------------------------

Statuses explanation:

* 📅: planned
* ✔️: done
* ❌: done as not supported
* 🔴: won't be implemented
* ❔: not decided yet

The version column specifies the API version which added the related method or
parameter. When no version is given, it means the item was introduced prior to
or with version 1.8.0.

All methods / pseudo-TOC
^^^^^^^^^^^^^^^^^^^^^^^^

.. table::
   :widths: 55 30 15

   ===========================  ======  =
   Method                       Vers.    
   ===========================  ======  =
   ping_                                ✔️
   getLicense_                          ✔️
   getMusicFolders_                     ✔️
   getIndexes_                          ✔️
   getMusicDirectory_                   ✔️
   getGenres_                   1.9.0   ✔️
   getArtists_                          ✔️
   getArtist_                           ✔️
   getAlbum_                            ✔️
   getSong_                             ✔️
   getVideos_                           ❌
   getVideoInfo_                1.15.0  🔴
   getArtistInfo_               1.11.0  📅
   getArtistInfo2_              1.11.0  📅
   getAlbumInfo_                1.14.0  📅
   getAlbumInfo2_               1.14.0  📅
   getSimilarSongs_             1.11.0  ❔
   getSimilarSongs2_            1.11.0  ❔
   getTopSongs_                 1.13.0  ❔
   getAlbumList_                        ✔️
   getAlbumList2_                       ✔️
   getRandomSongs_                      ✔️
   getSongsByGenre_             1.9.0   ✔️
   getNowPlaying_                       ✔️
   getStarred_                          ✔️
   getStarred2_                         ✔️
   :ref:`search <search->`              ✔️
   search2_                             ✔️
   search3_                             ✔️
   getPlaylists_                        ✔️
   getPlaylist_                         ✔️
   createPlaylist_                      ✔️
   updatePlaylist_                      ✔️
   deletePlaylist_                      ✔️
   stream_                              ✔️
   download_                            ✔️
   hls_                         1.9.0   ❌
   getCaptions_                 1.15.0  🔴
   getCoverArt_                         ✔️
   getLyrics_                           ✔️
   getAvatar_                           ❌
   star_                                ✔️
   unstar_                              ✔️
   setRating_                           ✔️
   scrobble_                            ✔️
   getShares_                           ❌
   createShare_                         ❌
   updateShare_                         ❌
   deleteShare_                         ❌
   getPodcasts_                         ❔
   getNewestPodcasts_           1.14.0  ❔
   refreshPodcasts_             1.9.0   ❔
   createPodcastChannel_        1.9.0   ❔
   deletePodcastChannel_        1.9.0   ❔
   deletePodcastEpisode_        1.9.0   ❔
   downloadPodcastEpisode_      1.9.0   ❔
   jukeboxControl_                      ✔️
   getInternetRadioStations_    1.9.0   ✔️
   createInternetRadioStation_  1.16.0  ✔️
   updateInternetRadioStation_  1.16.0  ✔️
   deleteInternetRadioStation_  1.16.0  ✔️
   getChatMessages_                     ✔️
   addChatMessage_                      ✔️
   getUser_                             ✔️
   getUsers_                    1.9.0   ✔️
   createUser_                          ✔️
   updateUser_                  1.10.2  ✔️
   deleteUser_                          ✔️
   changePassword_                      ✔️
   getBookmarks_                1.9.0   ❔
   createBookmark_              1.9.0   ❔
   deleteBookmark_              1.9.0   ❔
   getPlayQueue_                1.12.0  ❔
   savePlayQueue_               1.12.0  ❔
   getScanStatus_               1.15.0  ✔️
   startScan_                   1.15.0  ✔️
   ===========================  ======  =

Global
^^^^^^

Parameters used for any request

.. table::
   :widths: 55 30 15

   =====  ======  =
   P.     Vers.    
   =====  ======  =
   ``u``          ✔️
   ``p``          ✔️
   ``t``  1.13.0  🔴
   ``s``  1.13.0  🔴
   ``v``          ✔️
   ``c``          ✔️
   ``f``          ✔️
   =====  ======  =

Error codes

.. table::
   :widths: 55 30 15

   ==  ======  =
   #   Vers.    
   ==  ======  =
   0           ✔️
   10          ✔️
   20          ✔️
   30          ✔️
   40          ✔️
   41  1.15.0  📅
   50          ✔️
   60          ✔️
   70          ✔️
   ==  ======  =

System
^^^^^^

.. _ping:

``ping``
   ✔️

   No parameter

.. _getLicense:

``getLicense``
   ✔️

   No parameter

Browsing
^^^^^^^^

.. _getMusicFolders:

``getMusicFolders``
   ✔️

   No parameter

.. _getIndexes:

``getIndexes``
   ✔️

   .. table::
      :widths: 55 30 15

      ===================  =====  =
      Parameter            Vers.   
      ===================  =====  =
      ``musicFolderId``           ✔️
      ``ifModifiedSince``         ✔️
      ===================  =====  =

.. _getMusicDirectory:

``getMusicDirectory``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ✔️
      =========  =====  =

.. _getGenres:

``getGenres``
   ✔️ 1.9.0

   No parameter

.. _getArtists:

``getArtists``
   ✔️

   .. table::
      :widths: 55 30 15

      =================  ======  =
      Parameter          Vers.    
      =================  ======  =
      ``musicFolderId``  1.14.0  ✔️
      =================  ======  =

.. _getArtist:

``getArtist``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ✔️
      =========  =====  =

.. _getAlbum:

``getAlbum``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ✔️
      =========  =====  =

.. _getSong:

``getSong``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ✔️
      =========  =====  =

.. _getVideos:

``getVideos``
   ❌

   No parameter

.. _getVideoInfo:

``getVideoInfo``
   🔴 1.15.0

   .. table::
      :widths: 55 30 15

      =========  ======  =
      Parameter  Vers.   
      =========  ======  =
      ``id``     1.15.0  🔴
      =========  ======  =

.. _getArtistInfo:

``getArtistInfo``
   📅 1.11.0

   .. table::
      :widths: 55 30 15

      =====================  ======  =
      Parameter              Vers.    
      =====================  ======  =
      ``id``                 1.11.0  📅
      ``count``              1.11.0  📅
      ``includeNotPresent``  1.11.0  📅
      =====================  ======  =

.. _getArtistInfo2:

``getArtistInfo2``
   📅 1.11.0

   .. table::
      :widths: 55 30 15

      =====================  ======  =
      Parameter              Vers.    
      =====================  ======  =
      ``id``                 1.11.0  📅
      ``count``              1.11.0  📅
      ``includeNotPresent``  1.11.0  📅
      =====================  ======  =

.. _getAlbumInfo:

``getAlbumInfo``
   📅 1.14.0

   .. table::
      :widths: 55 30 15

      =========  ======  =
      Parameter  Vers.    
      =========  ======  =
      ``id``     1.14.0  📅
      =========  ======  =

.. _getAlbumInfo2:

``getAlbumInfo2``
   📅 1.14.0

   .. table::
      :widths: 55 30 15

      =========  ======  =
      Parameter  Vers.    
      =========  ======  =
      ``id``     1.14.0  📅
      =========  ======  =

.. _getSimilarSongs:

``getSimilarSongs``
   ❔ 1.11.0

   .. table::
      :widths: 55 30 15

      =========  ======  =
      Parameter  Vers.    
      =========  ======  =
      ``id``     1.11.0  ❔
      ``count``  1.11.0  ❔
      =========  ======  =

.. _getSimilarSongs2:

``getSimilarSongs2``
   ❔ 1.11.0

   .. table::
      :widths: 55 30 15

      =========  ======  =
      Parameter  Vers.    
      =========  ======  =
      ``id``     1.11.0  ❔
      ``count``  1.11.0  ❔
      =========  ======  =

.. _getTopSongs:

``getTopSongs``
   ❔ 1.13.0

   .. table::
      :widths: 55 30 15

      ==========  ======  =
      Parameter   Vers.    
      ==========  ======  =
      ``artist``  1.13.0  ❔
      ``count``   1.13.0  ❔
      ==========  ======  =

Album/song lists
^^^^^^^^^^^^^^^^

.. _getAlbumList:

``getAlbumList``
   ✔️

   .. table::
      :widths: 55 30 15

      =================  ======  =
      Parameter          Vers.    
      =================  ======  =
      ``type``                   ✔️
      ``size``                   ✔️
      ``offset``                 ✔️
      ``fromYear``               ✔️
      ``toYear``                 ✔️
      ``genre``                  ✔️
      ``musicFolderId``  1.12.0  ✔️
      =================  ======  =

   .. versionadded:: 1.10.1
      ``byYear`` and ``byGenre`` were added to ``type``

.. _getAlbumList2:

``getAlbumList2``
   ✔️

   .. table::
      :widths: 55 30 15

      =================  ======  =
      Parameter          Vers.    
      =================  ======  =
      ``type``                   ✔️
      ``size``                   ✔️
      ``offset``                 ✔️
      ``fromYear``               ✔️
      ``toYear``                 ✔️
      ``genre``                  ✔️
      ``musicFolderId``  1.12.0  ✔️
      =================  ======  =

   .. versionadded:: 1.10.1
      ``byYear`` and ``byGenre`` were added to ``type``

.. _getRandomSongs:

``getRandomSongs``
   ✔️

   .. table::
      :widths: 55 30 15

      =================  =====  =
      Parameter          Vers.   
      =================  =====  =
      ``size``                  ✔️
      ``genre``                 ✔️
      ``fromYear``              ✔️
      ``toYear``                ✔️
      ``musicFolderId``         ✔️
      =================  =====  =

.. _getSongsByGenre:

``getSongsByGenre``
   ✔️ 1.9.0

   .. table::
      :widths: 55 30 15

      =================  ======  =
      Parameter          Vers.    
      =================  ======  =
      ``genre``          1.9.0   ✔️
      ``count``          1.9.0   ✔️
      ``offset``         1.9.0   ✔️
      ``musicFolderId``  1.12.0  ✔️
      =================  ======  =

.. _getNowPlaying:

``getNowPlaying``
   ✔️

   No parameter

.. _getStarred:

``getStarred``
   ✔️

   .. table::
      :widths: 55 30 15

      =================  ======  =
      Parameter          Vers.    
      =================  ======  =
      ``musicFolderId``  1.12.0  ✔️
      =================  ======  =

.. _getStarred2:

``getStarred2``
   ✔️

   .. table::
      :widths: 55 30 15

      =================  ======  =
      Parameter          Vers.    
      =================  ======  =
      ``musicFolderId``  1.12.0  ✔️
      =================  ======  =

Searching
^^^^^^^^^

.. _search-:

``search``
   ✔️

   .. table::
      :widths: 55 30 15

      =============  =====  =
      Parameter      Vers.   
      =============  =====  =
      ``artist``            ✔️
      ``album``             ✔️
      ``title``             ✔️
      ``any``               ✔️
      ``count``             ✔️
      ``offset``            ✔️
      ``newerThan``         ✔️
      =============  =====  =

.. _search2:

``search2``
   ✔️

   .. table::
      :widths: 55 30 15

      =================  ======  =
      Parameter          Vers.    
      =================  ======  =
      ``query``                  ✔️
      ``artistCount``            ✔️
      ``artistOffset``           ✔️
      ``albumCount``             ✔️
      ``albumOffset``            ✔️
      ``songCount``              ✔️
      ``songOffset``             ✔️
      ``musicFolderId``  1.12.0  ✔️
      =================  ======  =

.. _search3:

``search3``
   ✔️

   .. table::
      :widths: 55 30 15

      =================  ======  =
      Parameter          Vers.    
      =================  ======  =
      ``query``                  ✔️
      ``artistCount``            ✔️
      ``artistOffset``           ✔️
      ``albumCount``             ✔️
      ``albumOffset``            ✔️
      ``songCount``              ✔️
      ``songOffset``             ✔️
      ``musicFolderId``  1.12.0  ✔️
      =================  ======  =

Playlists
^^^^^^^^^

.. _getPlaylists:

``getPlaylists``
   ✔️

   .. table::
      :widths: 55 30 15

      ============  =====  =
      Parameter     Vers.   
      ============  =====  =
      ``username``         ✔️
      ============  =====  =

.. _getPlaylist:

``getPlaylist``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ✔️
      =========  =====  =

.. _createPlaylist:

``createPlaylist``
   ✔️

   .. table::
      :widths: 55 30 15

      ==============  =====  =
      Parameter       Vers.   
      ==============  =====  =
      ``playlistId``         ✔️
      ``name``               ✔️
      ``songId``             ✔️
      ==============  =====  =

.. _updatePlaylist:

``updatePlaylist``
   ✔️

   .. table::
      :widths: 55 30 15

      =====================  =====  =
      Parameter              Vers.   
      =====================  =====  =
      ``playlistId``                ✔️
      ``name``                      ✔️
      ``comment``                   ✔️
      ``public``             1.9.0  ✔️
      ``songIdToAdd``               ✔️
      ``songIndexToRemove``         ✔️
      =====================  =====  =

.. _deletePlaylist:

``deletePlaylist``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ✔️
      =========  =====  =

Media retrieval
^^^^^^^^^^^^^^^

.. _stream:

``stream``
   ✔️

   .. table::
      :widths: 55 30 15

      =========================  ======  =
      Parameter                  Vers.    
      =========================  ======  =
      ``id``                             ✔️
      ``maxBitRate``                     ✔️
      ``format``                         ✔️
      ``timeOffset``                     ❌
      ``size``                           ❌
      ``estimateContentLength``          ✔️
      ``converted``              1.15.0  🔴
      =========================  ======  =

.. _download:

``download``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ✔️
      =========  =====  =

.. _hls:

``hls``
   🔴 1.9.0

   .. table::
      :widths: 55 30 15

      ==============  ======  =
      Parameter       Vers.    
      ==============  ======  =
      ``id``          1.9.0   🔴
      ``bitRate``     1.9.0   🔴
      ``audioTrack``  1.15.0  🔴
      ==============  ======  =

.. _getCaptions:

``getCaptions``
   🔴 1.15.0

   .. table::
      :widths: 55 30 15

      ==========  ======  =
      Parameter    Vers.   
      ==========  ======  =
      ``id``      1.15.0  🔴
      ``format``  1.15.0  🔴
      ==========  ======  =

.. _getCoverArt:

``getCoverArt``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ✔️
      ``size``          ✔️
      =========  =====  =

.. _getLyrics:

``getLyrics``
   ✔️

   .. table::
      :widths: 55 30 15

      ==========  =====  =
      Parameter   Vers.   
      ==========  =====  =
      ``artist``         ✔️
      ``title``          ✔️
      ==========  =====  =

.. _getAvatar:

``getAvatar``
   ❌

   .. table::
      :widths: 55 30 15

      ============  =====  =
      Parameter     Vers.   
      ============  =====  =
      ``username``         ❌
      ============  =====  =

Media annotation
^^^^^^^^^^^^^^^^

.. _star:

``star``
   ✔️

   .. table::
      :widths: 55 30 15

      ============  =====  =
      Parameter     Vers.   
      ============  =====  =
      ``id``               ✔️
      ``albumId``          ✔️
      ``artistId``         ✔️
      ============  =====  =

.. _unstar:

``unstar``
   ✔️

   .. table::
      :widths: 55 30 15

      ============  =====  =
      Parameter     Vers.   
      ============  =====  =
      ``id``               ✔️
      ``albumId``          ✔️
      ``artistId``         ✔️
      ============  =====  =

.. _setRating:

``setRating``
   ✔️

   .. table::
      :widths: 55 30 15

      ==========  =====  =
      Parameter   Vers.   
      ==========  =====  =
      ``id``             ✔️
      ``rating``         ✔️
      ==========  =====  =

.. _scrobble:

``scrobble``
   ✔️

   .. table::
      :widths: 55 30 15

      ==============  =====  =
      Parameter       Vers.   
      ==============  =====  =
      ``id``                 ✔️
      ``time``        1.9.0  ✔️
      ``submission``         ✔️
      ==============  =====  =

Sharing
^^^^^^^

.. _getShares:

``getShares``
   ❌

   No parameter

.. _createShare:

``createShare``
   ❌

   .. table::
      :widths: 55 30 15

      ===============  =====  =
      Parameter        Vers.   
      ===============  =====  =
      ``id``                  ❌
      ``description``         ❌
      ``expires``             ❌
      ===============  =====  =

.. _updateShare:

``updateShare``
   ❌

   .. table::
      :widths: 55 30 15

      ===============  =====  =
      Parameter        Vers.   
      ===============  =====  =
      ``id``                  ❌
      ``description``         ❌
      ``expires``             ❌
      ===============  =====  =

.. _deleteShare:

``deleteShare``
   ❌

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``            ❌
      =========  =====  =

Podcast
^^^^^^^

.. _getPodcasts:

``getPodcasts``
   ❔

   .. table::
      :widths: 55 30 15

      ===================  =====  =
      Parameter            Vers.   
      ===================  =====  =
      ``includeEpisodes``  1.9.0  ❔
      ``id``               1.9.0  ❔
      ===================  =====  =

.. _getNewestPodcasts:

``getNewestPodcasts``
   ❔ 1.14.0

   .. table::
      :widths: 55 30 15

      =========  ======  =
      Parameter  Vers.    
      =========  ======  =
      ``count``  1.14.0  ❔
      =========  ======  =

.. _refreshPodcasts:

``refreshPodcasts``
   ❔ 1.9.0

   No parameter

.. _createPodcastChannel:

``createPodcastChannel``
   ❔ 1.9.0

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``url``    1.9.0  ❔
      =========  =====  =

.. _deletePodcastChannel:

``deletePodcastChannel``
   ❔ 1.9.0

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``     1.9.0  ❔
      =========  =====  =

.. _deletePodcastEpisode:

``deletePodcastEpisode``
   ❔ 1.9.0

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``     1.9.0  ❔
      =========  =====  =

.. _downloadPodcastEpisode:

``downloadPodcastEpisode``
   ❔ 1.9.0

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``id``     1.9.0  ❔
      =========  =====  =

Jukebox
^^^^^^^

.. _jukeboxControl:

``jukeboxControl``
   ✔️

   .. table::
      :widths: 55 30 15

      ==========  =====  =
      Parameter   Vers.   
      ==========  =====  =
      ``action``         ✔️
      ``index``          ✔️
      ``offset``         ✔️
      ``id``             ✔️
      ``gain``           ❌
      ==========  =====  =

Internet radio
^^^^^^^^^^^^^^

.. _getInternetRadioStations:

``getInternetRadioStations``
   ❔ 1.9.0

   No parameter

.. _createInternetRadioStation:

``createInternetRadioStation``
   ❔ 1.16.0

   .. table::
      :widths: 55 30 15

      ===============  ======  =
      Parameter        Vers.    
      ===============  ======  =
      ``streamUrl``    1.16.0  ❔
      ``name``         1.16.0  ❔
      ``homepageUrl``  1.16.0  ❔
      ===============  ======  =

.. _updateInternetRadioStation:

``updateInternetRadioStation``
   ❔ 1.16.0

   .. table::
      :widths: 55 30 15

      ===============  ======  =
      Parameter        Vers.    
      ===============  ======  =
      ``id``           1.16.0  ❔
      ``streamUrl``    1.16.0  ❔
      ``name``         1.16.0  ❔
      ``homepageUrl``  1.16.0  ❔
      ===============  ======  =

.. _deleteInternetRadioStation:

``deleteInternetRadioStation``
   ❔ 1.16.0

   .. table::
      :widths: 55 30 15

      ===============  ======  =
      Parameter        Vers.    
      ===============  ======  =
      ``id``           1.16.0  ❔
      ===============  ======  =

Chat
^^^^

.. _getChatMessages:

``getChatMessages``
   ✔️

   .. table::
      :widths: 55 30 15

      =========  =====  =
      Parameter  Vers.   
      =========  =====  =
      ``since``         ✔️
      =========  =====  =

.. _addChatMessage:

``addChatMessage``
   ✔️

   .. table::
      :widths: 55 30 15

      ===========  =====  =
      Parameter    Vers.   
      ===========  =====  =
      ``message``         ✔️
      ===========  =====  =

User management
^^^^^^^^^^^^^^^

.. _getUser:

``getUser``
   ✔️

   .. table::
      :widths: 55 30 15

      ============  =====  =
      Parameter     Vers.   
      ============  =====  =
      ``username``         ✔️
      ============  =====  =

.. _getUsers:

``getUsers``
   ✔️ 1.9.0

   No parameter

.. _createUser:

``createUser``
   ✔️

   .. table::
      :widths: 55 30 15

      =======================  ======  =
      Parameter                Vers.    
      =======================  ======  =
      ``username``                     ✔️
      ``password``                     ✔️
      ``email``                        ✔️
      ``ldapAuthenticated``             
      ``adminRole``                    ✔️
      ``settingsRole``                  
      ``streamRole``                    
      ``jukeboxRole``                  ✔️
      ``downloadRole``                  
      ``uploadRole``                    
      ``playlistRole``                  
      ``coverArtRole``                  
      ``commentRole``                   
      ``podcastRole``                   
      ``shareRole``                     
      ``videoConversionRole``  1.14.0   
      ``musicFolderId``        1.12.0  📅
      =======================  ======  =

.. _updateUser:

``updateUser``
   ✔️ 1.10.2

   .. table::
      :widths: 55 30 15

      =======================  ======  =
      Parameter                Vers.    
      =======================  ======  =
      ``username``             1.10.2  ✔️
      ``password``             1.10.2  ✔️
      ``email``                1.10.2  ✔️
      ``ldapAuthenticated``    1.10.2   
      ``adminRole``            1.10.2  ✔️
      ``settingsRole``         1.10.2   
      ``streamRole``           1.10.2   
      ``jukeboxRole``          1.10.2  ✔️
      ``downloadRole``         1.10.2   
      ``uploadRole``           1.10.2   
      ``coverArtRole``         1.10.2   
      ``commentRole``          1.10.2   
      ``podcastRole``          1.10.2   
      ``shareRole``            1.10.2   
      ``videoConversionRole``  1.14.0   
      ``musicFolderId``        1.12.0  📅
      ``maxBitRate``           1.13.0  📅
      =======================  ======  =

.. _deleteUser:

``deleteUser``
   ✔️

   .. table::
      :widths: 55 30 15

      ============  =====  =
      Parameter     Vers.   
      ============  =====  =
      ``username``         ✔️
      ============  =====  =

.. _changePassword:

``changePassword``
   ✔️

   .. table::
      :widths: 55 30 15

      ============  =====  =
      Parameter     Vers.   
      ============  =====  =
      ``username``         ✔️
      ``password``         ✔️
      ============  =====  =

Bookmarks
^^^^^^^^^

.. _getBookmarks:

``getBookmarks``
   ❔ 1.9.0

   No parameter

.. _createBookmark:

``createBookmark``
   ❔ 1.9.0

   .. table::
      :widths: 55 30 15

      ============  =====  =
      Parameter     Vers.   
      ============  =====  =
      ``id``        1.9.0  ❔
      ``position``  1.9.0  ❔
      ``comment``   1.9.0  ❔
      ============  =====  =

.. _deleteBookmark:

``deleteBookmark``
   ❔ 1.9.0

   .. table::
      :widths: 55 30 15

      ===============  =====  =
      Parameter        Vers.   
      ===============  =====  =
      ``id``           1.9.0  ❔
      ===============  =====  =

.. _getPlayQueue:

``getPlayQueue``
   ❔ 1.12.0

   No parameter

.. _savePlayQueue:

``savePlayQueue``
   ❔ 1.12.0

   .. table::
      :widths: 55 30 15

      ============  ======  =
      Parameter     Vers.    
      ============  ======  =
      ``id``        1.12.0  ❔
      ``current``   1.12.0  ❔
      ``position``  1.12.0  ❔
      ============  ======  =

Library scanning
^^^^^^^^^^^^^^^^

.. _getScanStatus:

``getScanStatus``
   ✔️ 1.15.0

   No parameter

.. _startScan:

``startScan``
   ✔️ 1.15.0

   No parameter

Changes by version
------------------

Version 1.9.0
^^^^^^^^^^^^^

Added methods:

* getGenres_
* getSongsByGenre_
* hls_
* refreshPodcasts_
* createPodcastChannel_
* deletePodcastChannel_
* deletePodcastEpisode_
* downloadPodcastEpisode_
* getInternetRadioStations_
* getUsers_
* getBookmarks_
* createBookmark_
* deleteBookmark_

Added method parameters:

* updatePlaylist_

  * ``public``

* scrobble_

  * ``time``

* getPodcasts_

  * ``includeEpisodes``
  * ``id``

Version 1.10.1
^^^^^^^^^^^^^^

Added method parameters:

* getAlbumList_

  * ``fromYear``
  * ``toYear``
  * ``genre``

* getAlbumList2_

  * ``fromYear``
  * ``toYear``
  * ``genre``

Version 1.10.2
^^^^^^^^^^^^^^

Added methods:

* updateUser_

Version 1.11.0
^^^^^^^^^^^^^^

Added methods:

* getArtistInfo_
* getArtistInfo2_
* getSimilarSongs_
* getSimilarSongs2_

Version 1.12.0
^^^^^^^^^^^^^^

Added methods:

* getPlayQueue_
* savePlayQueue_

Added method parameters:

* getAlbumList_

  * ``musicFolderId``

* getAlbumList2_

  * ``musicFolderId``

* getSongsByGenre_

  * ``musicFolderId``

* getStarred_

  * ``musicFolderId``

* getStarred2_

  * ``musicFolderId``

* search2_

  * ``musicFolderId``

* search3_

  * ``musicFolderId``

* createUser_

  * ``musicFolderId``

* updateUser_

  * ``musicFolderId``

Version 1.13.0
^^^^^^^^^^^^^^

Added global parameters:

* ``t``
* ``s``

Added methods:

* getTopSongs_

Added method parameters:

* updateUser_

  * ``maxBitRate``

Version 1.14.0
^^^^^^^^^^^^^^

Added methods:

* getAlbumInfo_
* getAlbumInfo2_
* getNewestPodcasts_

Added method parameters:

* getArtists_

  * ``musicFolderId``

* createUser_

  * ``videoConversionRole``

* updateUser_

  * ``videoConversionRole``

Version 1.15.0
^^^^^^^^^^^^^^

Added error code ``41``

Added methods:

* getVideoInfo_
* getCaptions_
* getScanStatus_
* startScan_

Added method parameters:

* stream_

  * ``converted``

* hls_

  * ``audioTrack``

Version 1.16.0
^^^^^^^^^^^^^^

Added methods:

* createInternetRadioStation_
* updateInternetRadioStation_
* deleteInternetRadioStation_
