import React, { useContext, useEffect, useMemo, useRef, useState } from "react";
import { CoreGlobalContext } from "services/core";
import { useNavigate } from "react-router-dom";
import { AuthHatch } from "services/oauth";
import LoadingLayout from "layouts/loading_layout";
import styles from "../static/signup.module.css";
import { 
    Select, 
    MenuItem, 
    makeStyles,
    Box, 
    FormControl, 
    InputLabel, 
    SelectChangeEvent
} from '@mui/material';


interface InputConfig {
    type: string;
    background_svg: string;
}


const SignUpLayoutLoader: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const navigate = useNavigate();

    useEffect(() => {
        if (context_data.gateway_ready.status) navigate(context_data.contacts_path.current);
    }, [navigate, context_data.gateway_ready]);

    if (context_data.gateway_ready.tried && !context_data.gateway_ready.status) {
        return (
            <SignUpLayout />
        );
    } else {
        return (
            <LoadingLayout />
        );
    }
};


const SignUpLayout: React.FC = () => {
    const context_data = useContext(CoreGlobalContext);
    if (!context_data) {
        throw new Error("Can't load CoreGlobalContext for oauth");
    }

    const auth_hatch = useContext(AuthHatch);
    if (!auth_hatch) {
        throw new Error("Can't load AuthHatch for oauth");
    }

    const navigate = useNavigate();

    const username_field_ref = useRef<HTMLInputElement>(null);
    const email_field_ref = useRef<HTMLInputElement>(null);
    const password_field_ref = useRef<HTMLInputElement>(null);

    const [input_config, setInputConfig] = useState<InputConfig>({"type": "password", 
        "background_svg": "../public/oauth/eye_closed.svg"});

    const [year, setYear] = useState<string>("2025");
    const [month, setMonth] = useState<string>("January");
    const [day, setDay] = useState<string>("1");

    const getMonthDays = (year: number, month: number) => {
        return Array.from({ length: new Date(year, month, 0).getDate() }, (_, i) => i + 1);
    };

    const current_year = new Date().getFullYear();
    let years = Array.from({ length: current_year + 1 - 1930 }, (_, i) => i + 1930);
    let months = [
        {"name": "January", "index": 1},
        {"name": "February", "index": 2},
        {"name": "March", "index": 3},
        {"name": "April", "index": 4},
        {"name": "May", "index": 5},
        {"name": "June", "index": 6},
        {"name": "July", "index": 7},
        {"name": "August", "index": 8},
        {"name": "September", "index": 9},
        {"name": "October", "index": 10},
        {"name": "November", "index": 11},
        {"name": "December", "index": 12},
    ];

    const fetchMonth = (month_name: string) => {
        const num_mn = months.find(mn => mn.name === month_name)?.index;
        if (num_mn) return num_mn;
        return 1;
    };

    const [days, setDays] = useState<number[]>(getMonthDays(Number(year), fetchMonth(month)));

    const handleYear = (event: SelectChangeEvent) => {
        setYear(event.target.value as string);
        setDays(getMonthDays(Number(year), fetchMonth(month)));
    };

    const handleMonth = (event: SelectChangeEvent) => {
        setMonth(event.target.value as string);
        setDays(getMonthDays(Number(year), fetchMonth(month)));
    };

    const handleDay = (event: SelectChangeEvent) => {
        setDay(event.target.value as string);
    };

    const showPassword = () => {
        if (password_field_ref.current) {
            if (password_field_ref.current.type === "password") {
                setInputConfig({"type": "text", 
                    "background_svg": "../oauth/eye_opened.svg"});
            } else {
                setInputConfig({"type": "password",
                    "background_svg": "../oauth/eye_closed.svg"});
            }
        }
    };

    const submitData = async () => {
        if (username_field_ref.current && email_field_ref.current && password_field_ref.current) {
            if (username_field_ref.current.value === "") {
                //
                console.warn("Username field can't be empty!");
                return;
            }

            if (email_field_ref.current.value === "") {
                //
                console.warn("Email field can't be empty!");
                return;
            }

            if (password_field_ref.current.value === "") {
                //
                console.warn("Password field can't be empty!");
                return;
            }

            const bday_date = new Date(Number(year), fetchMonth(month), Number(day));
            const status = await auth_hatch.signup(
                username_field_ref.current.value,
                email_field_ref.current.value,
                password_field_ref.current.value,
                bday_date.toISOString().split("T")[0],
            );
            
            if (status) {
                navigate(context_data.contacts_path.current);
            };
        }
    };

    return (
        <div id={styles.signupContainer}>
            <div id={styles.signupForm}>
                <div className={styles.sectionHeader}>general</div>
                <input type="text" placeholder="Your username" className={styles.field} maxLength={35} ref={username_field_ref}></input>
                <div className={styles.help}>
                    - lowercase characters only!
                </div>
                <div className={styles.sectionHeader}>safety</div>
                <input type="email" placeholder="Your email" className={styles.field} maxLength={35} id="email" ref={email_field_ref}></input>
                <div id={styles.passwordSection}>
                    <input type={input_config.type} placeholder="Your password" maxLength={25} id={styles.password} ref={password_field_ref}></input>
                    <div id={styles.signupShowPassword} onClick={() => showPassword()} style={{backgroundImage: `url(${input_config.background_svg})`}}></div>
                </div>
                <div className={styles.help}>
                    - make sure it's a strong one <br></br>
                    - don't share it with anyone, even us!
                </div>
                <div className={styles.sectionHeader}>
                    now state your birthday date!
                </div>

                <Box sx={{ 
                    width: "90%",
                    display: "flex", 
                    flexDirection: "row",
                    gap: 1,
                    marginTop: 2,
                }}>
                    <FormControl fullWidth>
                        <InputLabel sx={{ color: "var(--highlight)" }} id="select-year">Year</InputLabel>
                        <Select sx={{ 
                            color: "var(--highlight)", 
                            width: 100,
                            '& .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--elements)",
                            },
                            '&:hover .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--active_elements)",
                            },
                            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--active_elements)",
                            },
                        }}
                            labelId="select-year-label"
                            id="select-year-label"
                            value={year}
                            label="Year"
                            onChange={handleYear}
                            MenuProps={{
                                PaperProps: {
                                    sx: {
                                        backgroundColor: "var(--elements)",
                                    },
                                    className: "hide_scrollbar",
                                },
                                style: {
                                    maxHeight: 250,
                                }
                            }}
                        >   
                            {years.reverse().map(yr => (
                                <MenuItem sx={{color: "white"}} value={yr}>{yr}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl fullWidth>
                        <InputLabel sx={{ color: "var(--highlight)" }} id="select-month">Month</InputLabel>
                        <Select sx={{ 
                            color: "var(--highlight)", 
                            width: 100,
                            '& .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--elements)",
                            },
                            '&:hover .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--active_elements)",
                            },
                            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--active_elements)",
                            },
                        }}
                            labelId="select-month-label"
                            id="select-month-label"
                            value={month}
                            label="Month"
                            onChange={handleMonth}
                            MenuProps={{
                                PaperProps: {
                                    sx: {
                                        backgroundColor: "var(--elements)",
                                    },
                                    className: 'hide_scrollbar',
                                },
                                style: {
                                    maxHeight: 250,
                                }
                            }}
                        >   
                            {months.map(mn => (
                                <MenuItem sx={{color: "white"}} value={mn.name}>{mn.name}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl fullWidth>
                        <InputLabel sx={{ color: "var(--highlight)" }} id="select-day">Day</InputLabel>
                        <Select sx={{ 
                            color: "var(--highlight)", 
                            width: 100,
                            '& .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--elements)",
                            },
                            '&:hover .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--active_elements)",
                            },
                            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                                borderColor: "var(--active_elements)",
                            },
                        }}
                            labelId="select-day-label"
                            id="select-day-label"
                            value={day}
                            label="Day"
                            onChange={handleDay}
                            MenuProps={{
                                PaperProps: {
                                    sx: {
                                        backgroundColor: "var(--elements)",
                                    },
                                    className: 'hide_scrollbar',
                                },
                                style: {
                                    maxHeight: 250,
                                },
                            }}
                        >   
                            {days.map(dy => (
                                <MenuItem sx={{color: "white"}} value={dy}>{dy}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Box>

                <div id={styles.createAccount} onClick={() => submitData()}>Create account!</div>
                <div id={styles.loginInstead} onClick={() => navigate(context_data.login_path.current)}>I already have an account!</div>
            </div>
        </div>
    );
};

export default SignUpLayoutLoader;