UPDATE track SET bitrate=bitrate/1000 WHERE bitrate > 16000 AND path NOT LIKE '%.wav';
