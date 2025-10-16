import { useEffect, useRef, useState, Dispatch, SetStateAction, use, ReactNode, useContext, createContext, RefObject } from "react";
import { io, Socket } from "socket.io-client";
import { DefaultEventsMap } from "@socket.io/component-emitter";
import { useLocation } from "react-router-dom";
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
import { AuthHatch } from "./oauth";
import { ErrorHandler } from "./error_assessor";
import { useNavigate } from "react-router-dom";


interface GatewayProperties {
    sendEvent: (event: string, data: object) => void;
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

const GatewayResponseSchema = z.object({
    status: z.boolean(),
    body: z.union([
        BasicSchema,
        MessageSchema,
        EssentialMessageSchema,
        EssentialClientSchema,
        NotificationSchema,
    ]).nullable(),
    error: ErrorSchema.nullable(), //Error can be null!
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
        throw new Error("[Listener] Can't load CoreGlobalContext for listener");
    }

    const auth_hatch = useContext(AuthHatch);
    if (!auth_hatch) {
        throw new Error("[Listener] Can't load AuthHatch for oauth");
    }

    const error_handler = useContext(ErrorHandler);
    if (!error_handler) {
        throw new Error("[Listener] Can't load CoreGlobalContext for oauth");
    }

    const gateway_ref = useRef<Socket<DefaultEventsMap, DefaultEventsMap>>(null);

    const emit_to_console = (type: string, data: string) => {
        switch (type) {
            case "error":
                console.error(`[Listener] ${data}`);
                break;
            case "warn":
                console.warn(`[Listener] ${data}`);
                break;
            case "log":
                console.log(`[Listener] ${data}`);
                break;
        }
    }

    useEffect(() => {
        if (!context_data.access_token) {
            emit_to_console("log", "No access token present, proceeding to refresh session");
            auth_hatch.refresh().then(status => {
                if (!status) {
                    context_data.setGatewayStatus(prev => ({
                        ...prev, tried: true
                    }));
                    emit_to_console("log", "Session refresh failed");
                }
                else emit_to_console("log", "Session refresh successful");
            })
            return;
        }

        if (!gateway_ref.current) {
            gateway_ref.current = io(context_data.core_server_host.current, {
                path: context_data.gateway_addr.current,
                auth: {"access_token": `${context_data.access_token}`},
                reconnection: true,
                transports: ["websocket"],
                reconnectionAttempts: context_data.max_reconnection_attempts.current,
                reconnectionDelay: context_data.reconnection_delay.current,
                reconnectionDelayMax: context_data.max_reconnection_delay.current,
                secure: false, //dev only!
            });
        }

        const gateway = gateway_ref.current;

        gateway.on("connect", () => {
            context_data.setGatewayStatus({"status": true, "tried": true});
            emit_to_console("log", "Successfully connected to gateway");
        });
        gateway.on("connect_error", (error) => {
            context_data.setGatewayStatus({"status": false, "tried": true});
            emit_to_console("error", `Gateway connection error has occured: ${error}`);
        });
        gateway.on("disconnect", (reason) => {
            context_data.setGatewayStatus({"status": false, "tried": false});
            emit_to_console("error", `Gateway disconnected: ${reason}`);
        });
        gateway.on("reconnect", (number) => {
            context_data.setGatewayStatus(prev => ({
                ...prev, status: true
            }));
            emit_to_console("error", `Gateway reconnected after ${number} attempts`);
        });
        gateway.on("reconnect_attempt", () => emit_to_console("error", "Attempting to reconnect to gateway..."));
        gateway.on("reconnect_failed", () => emit_to_console("error", "Reconnection to gateway failed, is the server dead?"));

        gateway.on("group_created", (data) => {
            const response = GatewayResponseSchema.safeParse(data);

            if (!response.success) {
                emit_to_console("warn", `Incoming request can't be processed: ${response.data}`);
                return;
            }

            const basic = BasicSchema.safeParse(response.data.body);

            if (!basic.success) {
                emit_to_console("warn", `Incoming request can't be processed: ${response.data.body}`);
                return;
            }

            const body: z.infer<typeof BasicSchema> = basic.data;
            const error: z.infer<typeof ErrorSchema> = response.data.error;

            if (!response.data.status) {
                if (error.index) {
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided"); //continue!!!
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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
                    error_handler.handle(error.index, error.target, "Listener");
                } else {
                    emit_to_console("error", "Can't display exact error, no index provided");
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

    }, [context_data.access_token]);

    
    const sendEvent = (event: string, data: object) => {
        if (gateway_ref.current) {
            try {
                gateway_ref.current.emit(event, data); //"event" stands for what?
            } catch (error) {
                emit_to_console("error", `Unable to send event data, gateway connection error: ${error}`);
            }
        } else {
            emit_to_console("error", "Gateway seems disconnected, unable to send data");
        }
    };

    return (
        <GatewayHatch.Provider value={{ sendEvent }}>
            { children }
        </GatewayHatch.Provider>
    );
};