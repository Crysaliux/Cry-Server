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

const ErrorSchema = z.object({
    index: z.string(),
    target: z.string(),
});

const FetchedRoomsSchema = z.object({
    spaces: z.array(SpaceSchema),
    rooms: z.array(RoomSchema),
});

const FetchedGroupSchema = z.object({
    spaces: z.array(SpaceSchema),
    rooms: z.array(RoomSchema),
    members: z.array(MemberSchema),
    primary_room_messages: z.array(MessageSchema), //first channel to be loaded
    primary_room_id: z.string(), //latest messages
});

const ResponseSchema = z.object({ //hbb - handled by backend
    status: z.boolean(),
    response: z.union([
        ErrorSchema,
        z.array(GroupSchema), //[hbb] here we fetch all groups
        z.array(RoleSchema), //[hbb] here we fetch all roles
        PermissionsTableSchema, //fetching all permissions for some role
        FetchedRoomsSchema, //[hbb] both spaces and rooms are being fetched here
        FetchedGroupSchema, //[hbb] In case group needs to be loaded
        z.array(MessageSchema), //messages (up too 100 at once!) are being fetched here
        z.array(MemberSchema), //[hbb] group members (up too 50 at once!) are being fetched here
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

export const APIListener = () => {
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
        const fetch_group = async (id: string, room_id: string | null) => {
            await __fetch_group(id, room_id);
        };
        const fetch_messages = async (group_id: string, room_id: string) => {
            await __fetch_messages(group_id, room_id);
        };

        const parts = location.pathname.split("/").filter(Boolean);
        if (parts.length < 1) return;

        const [group_id, room_id] = parts;
        if (group_id) {
            if (room_id) {
                if (!context_data.current_group.current) {
                    throw new Error("Current group undefined, can't fetch!");
                }

                if (context_data.current_group.current.id !== group_id) fetch_group(group_id, room_id);
                else fetch_messages(group_id, room_id);
            }
            else fetch_group(group_id, null);
        }

    }, [location]);

    /*
    APIListener's url handler:
        Every url gets fetched and checked to see whether it contains a single group url or both
        group and room urls.

        If only group url is present:
            The corresponding group is fully fetched, yet the url might as well be the group's global name.
            Backend accepts both.

            Chat from the first group's room is fetched.

        If both group and room urls are present:
            The corresponding group is fully fetched along with the specified room's chat.

    */

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
            const error = ErrorSchema.safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data.index, error.data.target);
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
            const error = ErrorSchema.safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data.index, error.data.target);
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
            const error = ErrorSchema.safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data.index, error.data.target);
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
            const error = ErrorSchema.safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data.index, error.data.target);
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

    const __fetch_permstable = async (group_id: string, room_id: string, role_id: string) => {
        const response = await APIHatch.get("/fetch_permstable", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id, room_id: room_id, role_id: role_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Permissions table fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data.index, error.data.target);
        }

        const actual = PermissionsTableSchema.safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Permissions table fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }
        
        const fetched_permstable: z.infer<typeof PermissionsTableSchema> = actual.data;

        set_permstable(fetched_permstable);
    };

    const __fetch_messages = async (group_id: string, room_id: string) => {
        const response = await APIHatch.get("/fetch_messages", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id, room_id: room_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Messages fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data.index, error.data.target);
        }

        const actual = z.array(MessageSchema).safeParse(parsed_response.data.response);

        if (!actual.success) {
            console.error(`Messages fetch failed, can't process server response: ${parsed_response.data.response}`);
            return;
        }

        const ms_type = z.array(MessageSchema)
        const fetched_messages: z.infer<typeof ms_type> = actual.data;

        set_objects("messages", transform(fetched_messages));
    };

    const __fetch_group = async (id: string, room_id: string | null) => {
        const response = await APIHatch.get("/fetch_group", {
            headers: { session_token: SessionTokenReference.current, id: id, room_id: room_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Group fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.response);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            useErrorHandler(error.data.index, error.data.target);
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
        set_objects("messages", transform(fetched_group.primary_room_messages));
    };

    return null;
};