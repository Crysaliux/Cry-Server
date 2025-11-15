RDServer - Remote Dictionary Server
RTMServer - Real Time Messaging Server

Error codes:

- database:
    100 - trouble connecting to the database server
    101 - database conenction timed out
    102 - database integrity violated
    103 - invalid database request
    104 - unexpocted database server error

- RDServer
    200 - failed to validate response modal
    201 - network error upon request
    202 - unexpected error upon request

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