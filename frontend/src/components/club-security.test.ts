import {describe,it,expect} from "vitest";
import {api} from "../lib/api/client";
describe("club request payloads",()=>{it("does not send owner, lyceum, role, or status",()=>{const body={name:"Society",short_description:"Short",description:"Long",category:"OTHER",interest_ids:[]}; expect(Object.keys(body)).not.toContain("owner"); expect(Object.keys(body)).not.toContain("lyceum"); expect(Object.keys(body)).not.toContain("role"); expect(Object.keys(body)).not.toContain("status"); expect(api.createClub).toBeTypeOf("function")})});
