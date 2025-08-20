import { useEffect, useContext, useRef } from "react";
import { CoreGlobalContext } from "./core";
import axios, { AxiosInstance } from "axios";
import { useLocation, useNavigate } from "react-router-dom";
import { z, ZodRawShape, ZodObject } from "zod";
import { APIHatch } from "./listener";
import { useObjects } from "./worker";
import { useErrorHandler } from "./handlers/error_handler";
import { 
    Client,
    Group, 
    Message, 
    PermissionsTable, 
    Role, 
    Room, 
    Space, 
    Notification,
    Member,

    ClientSchema,
    GroupSchema,
    MessageSchema,
    PermissionsTableSchema,
    RoleSchema,
    RoomSchema,
    SpaceSchema,
    NotificationSchema,
    MemberSchema,
} from "components/index";

//Fetch core global context
const context_data = useContext(CoreGlobalContext);
if (!context_data) {
    throw new Error("Can't load CoreGlobalContext for oauth");
}

const FetchedRoomsSchema = z.object({
    spaces: z.array(SpaceSchema),
    rooms: z.array(RoomSchema),
});

const FetchedGroupSchema = z.object({
    spaces: z.array(SpaceSchema),
    rooms: z.array(RoomSchema),
    members: z.array(MemberSchema),
    primary_channel_messages: z.array(MessageSchema), //first channel to be loaded
    primary_channel_id: z.string(), //latest messages
});

const ResponseSchema = z.object({
    status: z.boolean(),
    response: z.union([
        z.string(),
        z.array(GroupSchema), //here we fetch all groups
        z.array(RoleSchema), //here we fetch all roles
        PermissionsTableSchema, //fetching all permissions for some role
        FetchedRoomsSchema, //both spaces and rooms are being fetched here
        FetchedGroupSchema, //In case group needs to be loaded
        z.array(MessageSchema), //messages (up too 100 at once!) are being fetched here
        z.array(MemberSchema), //group members (up too 50 at once!) are being fetched here
    ]),
});

/*
response can be:
- an array of groups
- arrays of spaces & rooms
- an array of group members
- an array of messages
- an error string
- arrays or spaces & rooms & members &  primary channel's messages and primary channel's id
*/

export const Authentication = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const set_objects = useObjects((state) => state.setObjects);
    const set_permstable = useObjects((state) => state.setPermissionsTable);
    const SessionTokenReference = useRef<string | null>(null);

    const transform = (object_array: Group[] | Space[] | Room[] | Member[] | Message[] | Role[]) => {
        const transobj = Object.fromEntries(object_array.map(item => [item.id, item]));
        return transobj
    };

    useEffect(() => {
        const fetch_group = async (id: string, room_id: string) => {
            await __fetch_group(id, room_id);
        };

        const parts = location.pathname.split("/").filter(Boolean);
        if (parts.length < 1) return;

        const [group_id, room_id] = parts;
        if (group_id) fetch_group(group_id, room_id);

    }, [location]);


    const __fetch_groups = async () => {
        const response = await APIHatch.get("/fetch_groups", {
            headers: { session_token: SessionTokenReference.current },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Groups fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = z.string().safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data, "fetch_groups");
        }

        const actual = z.array(GroupSchema).safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Groups fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }
        
        const gs_type = z.array(GroupSchema);
        const fetched_groups: z.infer<typeof gs_type> = actual.data;

        set_objects("groups", transform(fetched_groups));
    };

    const __fetch_rooms = async (group_id: string) => {
        const response = await APIHatch.get("/fetch_rooms", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Rooms fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = z.string().safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data, "fetch_rooms");
        }

        const actual = FetchedRoomsSchema.safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Rooms fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }

        const fetched_rooms: z.infer<typeof FetchedRoomsSchema> = actual.data;

        set_objects("spaces", transform(fetched_rooms.spaces));
        set_objects("rooms", transform(fetched_rooms.rooms));
    };

    const __fetch_members = async (group_id: string) => {
        const response = await APIHatch.get("/fetch_members", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Members fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = z.string().safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data, "fetch_members");
        }

        const actual = z.array(MemberSchema).safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Members fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }
        
        const ms_type = z.array(MemberSchema);
        const fetched_members: z.infer<typeof ms_type> = actual.data;

        set_objects("members", transform(fetched_members));
    };

    const __fetch_roles = async (group_id: string) => {
        const response = await APIHatch.get("/fetch_roles", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Roles fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = z.string().safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data, "fetch_roles");
        }

        const actual = z.array(RoleSchema).safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Roles fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }
        
        const rs_type = z.array(RoleSchema);
        const fetched_roles: z.infer<typeof rs_type> = actual.data;

        set_objects("roles", transform(fetched_roles));
    };

    const __fetch_permstable = async (role_id: string, group_id: string) => {
        const response = await APIHatch.get("/fetch_permstable", {
            headers: { session_token: SessionTokenReference.current, role_id: role_id, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Permissions table fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = z.string().safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data, "fetch_permtable");
        }

        const actual = PermissionsTableSchema.safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Permissions table fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }
        
        const fetched_permstable: z.infer<typeof PermissionsTableSchema> = actual.data;

        set_permstable(fetched_permstable);
    };

    const __fetch_room = async (id: string, room_id: string) => {
        const response = await APIHatch.get("/fetch_room", {
            headers: { session_token: SessionTokenReference.current, id: id, room_id: room_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Room fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = z.string().safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data, "fetch_room");
        }

        const actual = z.array(MessageSchema).safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Room fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }

        const ms_type = z.array(MessageSchema)
        const fetched_messages: z.infer<typeof ms_type> = actual.data;

        set_objects("messages", transform(fetched_messages));
    };

    const __fetch_group = async (id: string, group_id: string) => {
        const response = await APIHatch.get("/fetch_group", {
            headers: { session_token: SessionTokenReference.current, id: id, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Group fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = z.string().safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data, "fetch_group");
        }

        const actual = FetchedGroupSchema.safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Group fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }

        const fetched_group: z.infer<typeof FetchedGroupSchema> = actual.data;

        set_objects("spaces", transform(fetched_group.spaces));
        set_objects("rooms", transform(fetched_group.rooms));
        set_objects("members", transform(fetched_group.members));
        set_objects("messages", transform(fetched_group.primary_channel_messages));
    };
};

/*
To do list:
- add session token handlers
- add proper __fetch... handlers
- 
*/