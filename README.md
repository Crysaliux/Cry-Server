RDServer - Remote Dictionary Server
RTMServer - Real Time Messaging Server

Error codes:

- database:
    100 - trouble connecting to the database server
    101 - database conenction timed out
    102 - database integrity violated
    103 - invalid database request
    104 - unexpected database server error

- RDServer
    200 - server disconnected
    201 - failed to set data
    202 - data validation error
    203 - execution error
    204 - skipped empty update
    205 - unexpected error during update process
    206 - no existing data found
    207 - data not found or could not be deleted
    208 - unexpected error upon deleting data

- Oauth/events
    300 - session refresh failed
    301 - session expired
    302 - username exists
    303 - email exist
    304 - too young
    305 - client not found
    306 - group not found
    307 - space not found
    308 - room not found
    309 - message not found
    310 - failed to save file(s)
    311 - global name exists
    312 - missing permissions
    313 - session token decoding failed


RDServer (Redis server):

- Cache port: 6380
- Session port: 6381