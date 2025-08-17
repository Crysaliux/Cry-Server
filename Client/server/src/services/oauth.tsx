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
        z.array(PermissionsTableSchema), //fetching all permissions for some role
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
    const set_objects = useObjects((state) => state.setObjects)
    const SessionTokenReference = useRef<string | null>(null);

    useEffect(() => {
        const fetch_group = async (id: string, room_id: string) => {
            await __fetch_group(id, room_id);
        };

        const parts = location.pathname.split("/").filter(Boolean);
        if (parts.length < 1) return;

        const [group_id, room_id] = parts;
        if (group_id) fetch_group(group_id, room_id);

    }, [location]);

    const __fetch_group = async (id: string, room_id: string) => {
        const response = await APIHatch.get("/fetch_group", {
            headers: { session_token: SessionTokenReference.current, id: id, room_id: room_id },
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

        set_objects("spaces", fetched_group.spaces); //think of a way to assign id's without breaking TS's typing
    };
};

/*
To do list:
- add session token handlers
- add proper __fetch... handlers
- 
*/