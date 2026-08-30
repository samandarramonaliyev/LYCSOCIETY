import {useParams} from "react-router-dom"; import {ClubDetailPage} from "./Clubs"; import {ReportAction} from "../components/ReportAction";
export function ReportedClubDetail(){const {clubId}=useParams(); return <><ClubDetailPage/>{clubId&&<ReportAction target_type="CLUB" target_id={clubId}/>}</>}
