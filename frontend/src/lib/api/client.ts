import type {ApiError,CurrentUser} from "../../types/api";
const base=import.meta.env.VITE_API_BASE_URL||"/api/v1";
function csrf(){ return document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1] ?? ""; }
export async function request<T>(path:string, init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers); headers.set("Accept","application/json"); if(init.body) headers.set("Content-Type","application/json"); const token=csrf(); if(token) headers.set("X-CSRFToken",decodeURIComponent(token));
 let response:Response; try{ response=await fetch(`${base}${path}`,{...init,headers,credentials:"include"}); }catch{ throw {message:"Network unavailable."} satisfies ApiError; }
 const data=await response.json().catch(()=>null); if(!response.ok) throw {message:data?.detail||data?.error?.message||"Request failed.",code:data?.error?.code} satisfies ApiError; return data as T;
}
export const api={ csrf:()=>request<{csrf_token:string}>("/auth/csrf/"), authenticate:(init_data:string)=>request<{user:CurrentUser}>("/auth/telegram/",{method:"POST",body:JSON.stringify({init_data})}), me:()=>request<CurrentUser>("/auth/me/"), lyceums:()=>request<{results:{id:string;name:string;code:string}[]}>("/verification/lyceums/"), claim:(data:Record<string,string>)=>request<{user:CurrentUser}>("/verification/claim/",{method:"POST",body:JSON.stringify(data)}), profile:()=>request<any>("/profile/"), interests:()=>request<{results:Interest[]}>("/interests/"), updateProfile:(data:unknown)=>request<any>("/profile/",{method:"PATCH",body:JSON.stringify(data)}) };
