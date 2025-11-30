RDServer - Remote Dictionary Server
RTMServer - Real Time Messaging Server

Error codes:

- database:
    100 - trouble connecting to the database server\n
    101 - database conenction timed out\n
    102 - database integrity violated\n
    103 - invalid database request\n
    104 - unexpected database server error\n

- RDServer
    200 - server disconnected\n
    201 - failed to set data\n
    202 - data validation error\n
    203 - execution error\n
    204 - skipped empty update\n
    205 - unexpected error during update process\n
    206 - no existing data found\n
    207 - data not found or could not be deleted\n
    208 - unexpected error upon deleting data\n

- Oauth/events
    300 - ...\n
    301 - session expired\n
    302 - username exists\n
    303 - email exist\n
    304 - too young\n
    305 - client not found\n
    306 - group not found\n
    307 - space not found\n
    308 - room not found\n
    309 - message not found\n
    310 - failed to save file(s)\n
    311 - global name exists\n
    312 - missing permissions\n
    313 - session token decoding failed\n
    314 - invalid session token\n
    315 - refresh token decoding failed\n
    316 - refresh token expired\n
    317 - invalid refresh token\n
    318 - invalid credentials\n


RDServer (Redis server):

- Cache port: 6380
- Session port: 6381