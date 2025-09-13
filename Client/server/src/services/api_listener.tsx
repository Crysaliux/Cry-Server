import { useContext, useRef, createContext, ReactNode } from "react";
import { CoreGlobalContext } from "./core";
import axios, { AxiosInstance } from "axios";
import { useNavigate } from "react-router-dom";
import { nullable, z } from "zod";
import { useObjects } from "./worker";
import { ErrorHandler } from "./handlers/error_handler";
import { 
    Group, 
    Message, 
    Role, 
    Room, 
    Space, 
    Member,

    GroupSchema,
    MessageSchema,
    PermissionsTableSchema,
    RoleSchema,
    RoomSchema,
    SpaceSchema,
    MemberSchema,
} from "components/index";


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
    body: z.union([
        z.string(),
        z.array(GroupSchema), //[hbb] here we fetch all groups
        z.array(RoleSchema), //[hbb] here we fetch all roles
        PermissionsTableSchema, //fetching all permissions for some role
        FetchedRoomsSchema, //[hbb] both spaces and rooms are being fetched here
        FetchedGroupSchema, //[hbb] In case group needs to be loaded
        z.array(MessageSchema), //messages (up too 100 at once!) are being fetched here
        z.array(MemberSchema), //[hbb] group members (up too 50 at once!) are being fetched here
    ]),
    error: z.union([ErrorSchema.nullable()]),
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

interface APIListenerProperties {
    children: ReactNode;
}

interface APIProperties {
    fetchGroups: () => void;
    fetchRooms: (group_id: string) => void;
    fetchMembers: (group_id: string) => void;
    fetchRoles: (group_id: string) => void;
    fetchPermstable: (group_id: string, room_id: string, role_id: string) => void;
    fetchMessages: (group_id: string, room_id: string) => void;
    fetchGroup: (id: string, room_id: string) => void;
    fetchPrimaryRoom: (group_id: string) => void;
}

export const APIHatch = createContext<APIProperties | undefined>(undefined);

export const APIListener: React.FC<APIListenerProperties> = ({ children }) => {
    //Fetch core global context
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const APIrs: AxiosInstance = axios.create({
        baseURL: `${context_data.core_server_host.current}${context_data.api_hatch_addr.current}`,
        headers: {
            "session_token": `${context_data.session_token}`,
            "Content-Type": "application/json",
        },
    });

    const navigate = useNavigate();
    const set_objects = useObjects((state) => state.setObjects);
    const set_permstable = useObjects((state) => state.setPermissionsTable);
    const SessionTokenReference = useRef<string | null>(null);

    const transform = (object_array: Group[] | Space[] | Room[] | Member[] | Message[] | Role[]) => {
        const transobj = Object.fromEntries(object_array.map(item => [item.id, item]));
        return transobj
    };


    const __fetch_groups = async () => {
        const response = await APIrs.get("/fetch_groups", {
            headers: { session_token: SessionTokenReference.current },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Groups fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            ErrorHandler(error.data.index, error.data.target, navigate);
        }

        const actual = z.array(GroupSchema).safeParse(parsed_response.data.body);

        if (!actual.success) {
            console.error(`Groups fetch failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }
        
        const gs_type = z.array(GroupSchema);
        const fetched_groups: z.infer<typeof gs_type> = actual.data;

        set_objects("groups", transform(fetched_groups));
    };

    const __fetch_rooms = async (group_id: string) => {
        const response = await APIrs.get("/fetch_rooms", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Rooms fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            ErrorHandler(error.data.index, error.data.target, navigate);
        }

        const actual = FetchedRoomsSchema.safeParse(parsed_response.data.body);

        if (!actual.success) {
            console.error(`Rooms fetch failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }

        const fetched_rooms: z.infer<typeof FetchedRoomsSchema> = actual.data;

        set_objects("spaces", transform(fetched_rooms.spaces));
        set_objects("rooms", transform(fetched_rooms.rooms));
    };

    const __fetch_members = async (group_id: string) => {
        const response = await APIrs.get("/fetch_members", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Members fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            ErrorHandler(error.data.index, error.data.target, navigate);
        }

        const actual = z.array(MemberSchema).safeParse(parsed_response.data.body);

        if (!actual.success) {
            console.error(`Members fetch failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }
        
        const ms_type = z.array(MemberSchema);
        const fetched_members: z.infer<typeof ms_type> = actual.data;

        set_objects("members", transform(fetched_members));
    };

    const __fetch_roles = async (group_id: string) => {
        const response = await APIrs.get("/fetch_roles", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Roles fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            ErrorHandler(error.data.index, error.data.target, navigate);
        }

        const actual = z.array(RoleSchema).safeParse(parsed_response.data.body);

        if (!actual.success) {
            console.error(`Roles fetch failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }
        
        const rs_type = z.array(RoleSchema);
        const fetched_roles: z.infer<typeof rs_type> = actual.data;

        set_objects("roles", transform(fetched_roles));
    };

    const __fetch_permstable = async (group_id: string, room_id: string, role_id: string) => {
        const response = await APIrs.get("/fetch_permstable", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id, room_id: room_id, role_id: role_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Permissions table fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            ErrorHandler(error.data.index, error.data.target, navigate);
        }

        const actual = PermissionsTableSchema.safeParse(parsed_response.data.body);

        if (!actual.success) {
            console.error(`Permissions table fetch failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }
        
        const fetched_permstable: z.infer<typeof PermissionsTableSchema> = actual.data;

        set_permstable(fetched_permstable);
    };

    const __fetch_messages = async (group_id: string, room_id: string) => {
        const response = await APIrs.get("/fetch_messages", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id, room_id: room_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Messages fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            ErrorHandler(error.data.index, error.data.target, navigate);
        }

        const actual = z.array(MessageSchema).safeParse(parsed_response.data.body);

        if (!actual.success) {
            console.error(`Messages fetch failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }

        const ms_type = z.array(MessageSchema)
        const fetched_messages: z.infer<typeof ms_type> = actual.data;

        set_objects("messages", transform(fetched_messages));
    };

    const __fetch_group = async (id: string, room_id: string) => {
        const response = await APIrs.get("/fetch_group", {
            headers: { session_token: SessionTokenReference.current, id: id, room_id: room_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Group fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            ErrorHandler(error.data.index, error.data.target, navigate);
        }

        const actual = FetchedGroupSchema.safeParse(parsed_response.data.body);

        if (!actual.success) {
            console.error(`Group fetch failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }

        const fetched_group: z.infer<typeof FetchedGroupSchema> = actual.data;

        set_objects("spaces", transform(fetched_group.spaces));
        set_objects("rooms", transform(fetched_group.rooms));
        set_objects("members", transform(fetched_group.members));
        set_objects("messages", transform(fetched_group.primary_room_messages));
    };

    const __fetch_primary_room = async (group_id: string) => {
        const response = await APIrs.get("/fetch_group", {
            headers: { session_token: SessionTokenReference.current, group_id: group_id },
        });

        const parsed_response = ResponseSchema.safeParse(response);

        if (!parsed_response.success) {
            console.error(`Primary room id fetch failed, can't process server response: ${parsed_response.data}`);
            return;
        }

        if (!parsed_response.data.status) {
            const error = ErrorSchema.safeParse(parsed_response.data.error);
            if (!error.success) {
                console.error(`Can't display exact error, parsing failed: ${error.error.issues}`);
                return;
            }
            if (!error.data.index) {
                console.error("Can't display exact error, no index provided");
                return;
            }

            ErrorHandler(error.data.index, error.data.target, navigate);
        }

        const actual = z.string().safeParse(parsed_response.data.body);

        if (!actual.success) {
            console.error(`Primary room id fetch failed, can't process server response: ${parsed_response.data.body}`);
            return;
        }

        const room_id: z.infer<typeof z.string> = actual.data;

        return room_id;
    };

    const fetchGroups = async () => {
        await __fetch_groups();
    };

    const fetchRooms = async (group_id: string) => {
        await __fetch_rooms(group_id);
    };

    const fetchMembers = async (group_id: string) => {
        await __fetch_members(group_id);
    };

    const fetchRoles = async (group_id: string) => {
        await __fetch_roles(group_id);
    };

    const fetchPermstable = async (group_id: string, room_id: string, role_id: string) => {
        await __fetch_permstable(group_id, room_id, role_id);
    };

    const fetchMessages = async (group_id: string, room_id: string) => {
        await __fetch_messages(group_id, room_id);
    };

    const fetchGroup = async (id: string, room_id: string) => {
        await __fetch_group(id, room_id);
    };

    const fetchPrimaryRoom = async (group_id: string) => {
        return await __fetch_primary_room(group_id);
    };


    return (
        <APIHatch.Provider value={{ 
            fetchGroups,
            fetchRooms,
            fetchMembers,
            fetchRoles,
            fetchPermstable,
            fetchMessages,
            fetchGroup,
            fetchPrimaryRoom,
         }}>
            { children }
        </APIHatch.Provider>
    );
};