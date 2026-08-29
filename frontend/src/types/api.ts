export type AuthState = "INITIALIZING"|"TELEGRAM_UNAVAILABLE"|"AUTHENTICATING"|"UNVERIFIED"|"VERIFIED"|"SUSPENDED"|"ERROR";
export interface CurrentUser { account_status:string; verification_status:string; can_access_student_features:boolean; telegram?:{username:string;first_name:string;last_name:string}; profile?:{about:string;hobbies:string;profile_photo_url:string;interests:Interest[]}; verified_student?:{first_name:string;last_name:string;lyceum:{id:string;name:string;code?:string};group:string}; }
export interface Interest { id:string; name:string; slug:string; }
export interface ClubSummary { id:string; name:string; category:string; short_description:string; member_count:number; interests:Interest[]; }
export interface ApiError { code?:string; message:string; fields?:Record<string,string[]>; }
