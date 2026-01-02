RDServer - Remote Dictionary Server<br>
RTMServer - Real Time Messaging Server<br>

Error codes:

- database:<br>
    100 - trouble connecting to the database server<br>
    101 - database conenction timed out<br>
    102 - database integrity violated<br>
    103 - invalid database request<br>
    104 - unexpected database server error<br>

- RDServer:<br>
    200 - server disconnected<br>
    201 - failed to set data<br>
    202 - data validation error<br>
    203 - execution error<br>
    204 - skipped empty update<br>
    205 - unexpected error during update process<br>
    206 - no existing data found<br>
    207 - data not found or could not be deleted<br>
    208 - unexpected error upon deleting data<br>

- Oauth/events:<br>
    300 - ...<br>
    301 - session expired<br>
    302 - username exists<br>
    303 - email exists<br>
    304 - too young<br>
    305 - client not found<br>
    306 - group not found<br>
    307 - space not found<br>
    308 - room not found<br>
    309 - message not found<br>
    310 - failed to save file(s)<br>
    311 - global name exists<br>
    312 - missing permissions<br>
    313 - session token decoding failed<br>
    314 - invalid session token<br>
    315 - refresh token decoding failed<br>
    316 - refresh token expired<br>
    317 - invalid refresh token<br>
    318 - invalid credentials<br>
    319 - role-to-room permission not found<br>
    320 - global permission not found<br>
    321 - owner permission can't be removed<br>
    322 - client has been banned in this group<br>

RDServer (Redis server):<br>
    - Cache port: 6380<br>
    - Session port: 6381<br>
