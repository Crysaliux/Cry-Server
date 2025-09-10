import { useEffect, useRef, useState, Dispatch, SetStateAction, use, ReactNode, useContext, createContext, RefObject } from "react";
import { io } from "socket.io-client";
import { z, ZodRawShape, ZodObject } from "zod";
import { 
    Client,
    Group, 
    Message, 
    PermissionsTable, 
    Role, 
    Room, 
    Space, 
    Notification,

    ClientSchema,
    GroupSchema,
    MessageSchema,
    PermissionsTableSchema,
    RoleSchema,
    RoomSchema,
    SpaceSchema,
    NotificationSchema,
} from "components/index";
import axios, { AxiosInstance } from "axios";
import { CoreGlobalContext } from "./core";
import { useObjects } from "./worker";
import { ErrorHandler } from "./handlers/error_handler";
import { useNavigate } from "react-router-dom";


interface GatewayProperties {
    sendEvent: (data: object) => void;
}

interface ListenerProperties {
    children: ReactNode;
}

function essential<T extends z.ZodRawShape, K extends keyof T>(
    schema: z.ZodObject<T>,
    keys: readonly K[]
): z.ZodObject<any> {
    const partialSchema = schema.partial();

    const requiredKeys: Record<string, true> = {};
    keys.forEach((key) => {
        requiredKeys[key as string] = true;
    });
    return partialSchema.required(requiredKeys as unknown as Record<keyof T, true>);
}

const EssentialClientSchema = essential(ClientSchema, ["username", "nickname", "avatar_url", "id"]);
const EssentialMessageSchema = essential(MessageSchema, ["content", "id"]);

const BasicSchema = z.object({
    id: z.string(),
});

export const ErrorSchema = z.object({
    index: z.string(),
    target: z.string(),
});

const AccessErrorSchema = z.object({
    error: ErrorSchema,
})

const GatewayResponseSchema = z.object({
    status: z.boolean(),
    body: z.union([
        BasicSchema,
        MessageSchema,
        EssentialMessageSchema,
        EssentialClientSchema,
        NotificationSchema,
    ]),
    error: ErrorSchema,
});


/*
const parseResult = BasicSchema.safeParse(data.body);

if (parseResult.success) {
  const body: z.infer<typeof BasicSchema> = parseResult.data;
  // TS now knows body is Basic
} else {
  console.error("Invalid body:", parseResult.error);
  // handle error
}
*/

//Listener main body
export const GatewayHatch = createContext<GatewayProperties | undefined>(undefined);

export const Listener: React.FC<ListenerProperties> = ({ children }) => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for listener");
    }

    const gateway = io(context_data.core_server_host.current, {
        path: context_data.gateway_addr.current,
        auth: {"session_token": `${context_data.session_token}`},
        reconnection: true,
        transports: ["websocket"],
        reconnectionAttempts: context_data.max_reconnection_attempts.current,
        reconnectionDelay: context_data.reconnection_delay.current,
        reconnectionDelayMax: context_data.max_reconnection_delay.current,
    });

    const navigate = useNavigate();

    useEffect(() => {
        gateway.on("connect", () => console.log("Successfully connected to gateway"));
        gateway.on("connect_error", (error) => console.log(`Gateway connection error has occured: ${error}`));
        gateway.on("disconnect", (reason) => console.error(`Gateway disconnected: ${reason}`));
        gateway.on("reconnect", (number) => console.error(`Gateway reconnected after ${number} attempts`));
        gateway.on("reconnect_attempt", () => console.log("Attempting to reconnect to gateway..."));
        gateway.on("reconnect_failed", () => console.error("Reconnection to gateway failed, is the server dead?"));

        //Access handlers
        gateway.on("connection_refused", (data) => {
            const response = AccessErrorSchema.safeParse(data);
            
            if (!response.success) {
                console.warn(`Incoming request can't be processed: ${response.data}`); //why here only?
                return;
            }

            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
        });

        gateway.on("group_created", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                console.warn(`Incoming request can't be processed: ${response.data}`); //why here only?
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                console.warn(`Incoming request can't be processed: ${response.data.body}`);
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("space_created", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("room_created", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("message_sent", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = MessageSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof MessageSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("role_created", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("permissions_table_created", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });


        gateway.on("client_updated", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = EssentialClientSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof EssentialClientSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("group_updated", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("space_updated", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("room_updated", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("message_edited", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = EssentialMessageSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof EssentialMessageSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("role_updated", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("permissions_table_updated", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });


        gateway.on("client_deleted", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("group_deleted", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("space_deleted", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("room_deleted", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("message_deleted", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        gateway.on("role_deleted", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    ErrorHandler(error.index, error.target, navigate);
                } else {
                    console.error("Can't display exact error, no index provided");
                }
                return;
            }

            //to be continued..
        });

        return () => {
            gateway.off("connect");
            gateway.off("connect_error");
            gateway.off("disconnect");
            gateway.off("reconnect");
            gateway.off("reconnect_attempt");
            gateway.off("reconnect_failed");

            gateway.off("connection_refused");

            gateway.off("group_created");
            gateway.off("space_created");
            gateway.off("room_created");
            gateway.off("message_sent");
            gateway.off("role_created");
            gateway.off("permissions_table_created");


            gateway.off("client_updated");
            gateway.off("group_updated");
            gateway.off("space_updated");
            gateway.off("room_updated");
            gateway.off("message_edited");
            gateway.off("role_updated");
            gateway.off("permissions_table_updated");


            gateway.off("client_deleted");
            gateway.off("group_deleted");
            gateway.off("space_deleted");
            gateway.off("room_deleted");
            gateway.off("message_deleted");
            gateway.off("role_deleted");
        };

    }, []);

    
    const sendEvent = (data: object) => {
        try {
            gateway.emit("event", data);
        } catch (error) {
            console.error("Unable to send event data, gateway connection error");
        }
    };

    return (
        <GatewayHatch.Provider value={{ sendEvent }}>
            { children }
        </GatewayHatch.Provider>
    );
};