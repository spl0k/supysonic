Transcoding
===========

Transcoding is the process of converting from one audio format to another. This
allows for streaming of formats that wouldn't be streamable otherwise, or
reducing the quality of an audio file to allow a decent streaming for clients
with limited bandwidth, such as the ones running on a mobile connection.

Transcoding in Supysonic is achieved through the use of third-party command-line
programs. Supysonic isn't bundled with such programs, and you are left to choose
which one you want to use.

If you want to use transcoding but your client doesn't allow you to do so, you
can force Supysonic to transcode for that client by going to your profile page
on the web interface.

Configuration
-------------

Configuration of transcoders is done on the :ref:`conf-transcoding` of the
configuration file.

Transcoding can be done by one single program which is able to convert from one
format directly to another one, or by two programs: a decoder and an encoder.
All these are defined by the following variables:

* ``transcoder_EXT_EXT``
* ``decoder_EXT``
* ``encoder_EXT``
* ``trancoder``
* ``decoder``
* ``encoder``
* ``default_transcode_target``

where ``EXT`` is the lowercase file extension of the matching audio format.
``transcoder``\ s variables have two extensions: the first one is the source
extension, and the second one is the extension to convert to. The same way,
``decoder``\ s extension is the source extension, and ``encoder``\ s extension
is the extension to convert to.
The value of ``default_transcode_target`` will be used as output format when a
client requests a bitrate lower than the original file and no specific format.

Notice that all of them have a version without extension. Those are generic
versions. The programs defined with these variables should be able to
transcode/decode/encode any format. For that reason, we suggest you don't use
these if you want to keep control over the available transcoders.

Supysonic will take the first available transcoding configuration in the
following order:

#. specific transcoder
#. specific decoder / specific encoder
#. generic decoder / generic encoder (with the possibility to use a generic
   decoder with a specific encoder, and vice-versa)
#. generic transcoder

All the variables should be set to the command-line used to run the converter
program. The command-lines can include the following fields:

``%srcpath``
   path to the original file to transcode

``%srcfmt``
   extension of the original file

``%outfmt``
   extension of the resulting file

``%outrate``
   bitrate of the resulting file

``%title``
   title of the file to transcode

``%album``
   album name of the file to transcode

``%artist``
   artist name of the file to transcode

``%tracknumber``
   track number of the file to transcode

``%totaltracks``
   number of tracks in the album of the file to transcode

``%discnumber``
   disc number of the file to transcode

``%genre``
   genre of the file to transcode (not always available, defaults to "")

``%year``
   year of the file to transcode (not always available, defaults to "")

One final note: the original file should be provided as an argument of
transcoders and decoders. All transcoders, decoders and encoders should write
to standard output, and encoders should read from standard input (decoders
output being piped into encoders)

Suggested configuration
^^^^^^^^^^^^^^^^^^^^^^^

Here is an example configuration that you could use. This is provided as-is,
and some configurations haven't been tested.

.. highlight:: ini

Basic configuration::

   [transcoding]
   transcoder_mp3_mp3 = lame --quiet --mp3input -b %outrate %srcpath -
   transcoder = ffmpeg -i %srcpath -ab %outratek -v 0 -f %outfmt -
   decoder_mp3 = mpg123 --quiet -w - %srcpath
   decoder_ogg = oggdec -o %srcpath
   decoder_flac = flac -d -c -s %srcpath
   encoder_mp3 = lame --quiet -b %outrate - -
   encoder_ogg = oggenc2 -Q -M %outrate -
   default_transcode_target = mp3

To include track metadata in the transcoded stream::

   [transcoding]
   transcoder_mp3_mp3 = lame --quiet --mp3input -b %outrate --tt %title --tl %album --ta %artist --tn %tracknumber/%totaltracks --tv TPOS=%discnumber --tg %genre --ty %year --add-id3v2 %srcpath -
   transcoder = ffmpeg -i %srcpath -ab %outratek -v 0 -metadata title=%title -metadata album=%album -metadata author=%artist -metadata track=%tracknumber/%totaltracks -metadata disc=%discnumber -metadata genre=%genre -metadata date=%year -f %outfmt -
   decoder_mp3 = mpg123 --quiet -w - %srcpath
   decoder_ogg = oggdec -o %srcpath
   decoder_flac = flac -d -c -s %srcpath
   encoder_mp3 = lame --quiet -b %outrate --tt %title --tl %album --ta %artist --tn %tracknumber/%totaltracks --tv TPOS=%discnumber --tg %genre --ty %year --add-id3v2 - -
   encoder_ogg = oggenc2 -Q -M %outrate -t %title -l %album -a %artist -N %tracknumber -c TOTALTRACKS=%totaltracks -c DISCNUMBER=%discnumber -G %genre -d %year -
   default_transcode_target = mp3

.. _transcoding-enable:

Enabling transcoding
--------------------

Once the transcoding configuration has been set, most clients will require the
user to specify that they want to transcode files. This might be done on the
client itself, but most importantly it should be done on Supysonic web
interface. Not doing so might prevent some clients to properly request
transcoding.

To enable transcoding with the web interface, you should first start using the
client you want to set transcoding for. Only browsing the library should
suffice. Then open your browser of choice and navigate to the URL of your
Supysonic instance. Log in with your credentials and the click on your username
in the top bar. There you should be presented with a list of clients you used to
connect to Supysonic and be able to set your preferred streaming format
and bitrate.
