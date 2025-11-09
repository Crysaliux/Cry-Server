from ..worker import Client, Group
from typing import Any, Union

class Assign:
    def __init__(self):
        pass

"""
role = session.query(Role).filter_by(name="moderator").one()
channel = session.query(Channel).filter_by(name="general").one()

link = RoleToRoomPermission(
    role=role,
    channel=channel,
    can_send_message=True, 
    can_pin_message=True
)
session.add(link)
session.commit()

for link in role.channel_links:
    print(link.channel.name, link.can_send_message, link.can_pin_message)


FOR SPEED:

session.add_all([Permission(name=n) for n in names])
session.commit() !!!
"""