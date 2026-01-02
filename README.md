RDServer - Remote Dictionary Server__
RTMServer - Real Time Messaging Server____

Error codes:____

- database:__
    100 - trouble connecting to the database server__
    101 - database conenction timed out__
    102 - database integrity violated__
    103 - invalid database request__
    104 - unexpected database server error____

- RDServer__
    200 - server disconnected__
    201 - failed to set data__
    202 - data validation error__
    203 - execution error__
    204 - skipped empty update__
    205 - unexpected error during update process__
    206 - no existing data found__
    207 - data not found or could not be deleted__
    208 - unexpected error upon deleting data____

- Oauth/events:__
    300 - ...__
    301 - session expired__
    302 - username exists__
    303 - email exist__
    304 - too young__
    305 - client not found__
    306 - group not found__
    307 - space not found__
    308 - room not found__
    309 - message not found__
    310 - failed to save file(s)__
    311 - global name exists__
    312 - missing permissions__
    313 - session token decoding failed__
    314 - invalid session token__
    315 - refresh token decoding failed__
    316 - refresh token expired__
    317 - invalid refresh token__
    318 - invalid credentials__
    319 - role-to-room permission not found__
    320 - global permission not found__
    321 - owner permission can't be removed__
    322 - client has been banned in this group____

RDServer (Redis server):__
    - Cache port: 6380__
    - Session port: 6381__
