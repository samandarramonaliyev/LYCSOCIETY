export interface TelegramWebApp { initData:string; ready():void; expand():void; BackButton?:{show():void;hide():void;onClick(cb:()=>void):void}; HapticFeedback?:{impactOccurred(style:string):void}; viewportHeight?:number; }
declare global { interface Window { Telegram?:{WebApp?:TelegramWebApp} } }
export function telegram():TelegramWebApp|null { return window.Telegram?.WebApp ?? null; }
export function initializeTelegram(){ const app=telegram(); if(app){ app.ready(); app.expand(); } return app; }
