import {fireEvent,render,screen} from "@testing-library/react";
import {beforeEach,describe,expect,it,vi} from "vitest";
import {ReportAction} from "./ReportAction";
import {createReport} from "../lib/api/client";

vi.mock("../lib/api/client",()=>({createReport:vi.fn()}));

const mockedCreateReport=vi.mocked(createReport);

describe("ReportAction",()=>{
  beforeEach(()=>{mockedCreateReport.mockReset(); mockedCreateReport.mockResolvedValue({id:"r1",status:"OPEN"});});

  it("opens and submits a club report with only client-allowed fields",async()=>{
    render(<ReportAction target_type="CLUB" target_id="club-1"/>);
    fireEvent.click(screen.getByRole("button",{name:"Report Society"}));
    fireEvent.change(screen.getByLabelText("Reason"),{target:{value:"SPAM"}});
    fireEvent.click(screen.getByRole("button",{name:"Submit report"}));
    await screen.findByText("Report submitted. An administrator will review it.");
    expect(mockedCreateReport).toHaveBeenCalledWith({target_type:"CLUB",target_id:"club-1",reason:"SPAM"});
    const payload=mockedCreateReport.mock.calls[0][0] as unknown as Record<string,unknown>;
    for(const key of ["reporter","lyceum","status","reviewer","reviewed_at"]) expect(payload).not.toHaveProperty(key);
  });

  it("renders announcement action and sends the announcement target",async()=>{
    render(<ReportAction target_type="ANNOUNCEMENT" target_id="announcement-7"/>);
    expect(screen.getByRole("button",{name:"Report announcement"})).toBeTruthy();
    fireEvent.click(screen.getByRole("button",{name:"Report announcement"}));
    fireEvent.click(screen.getByRole("button",{name:"Submit report"}));
    await screen.findByText("Report submitted. An administrator will review it.");
    expect(mockedCreateReport).toHaveBeenCalledWith({target_type:"ANNOUNCEMENT",target_id:"announcement-7",reason:"SPAM"});
  });

  it("requires details when OTHER is selected",()=>{
    render(<ReportAction target_type="CLUB" target_id="club-2"/>);
    fireEvent.click(screen.getByRole("button",{name:"Report Society"}));
    fireEvent.change(screen.getByLabelText("Reason"),{target:{value:"OTHER"}});
    fireEvent.click(screen.getByRole("button",{name:"Submit report"}));
    expect(screen.getByText("Please add details for this reason.")).toBeTruthy();
    expect(mockedCreateReport).not.toHaveBeenCalled();
  });

  it("keeps a safe failure state without showing success",async()=>{
    mockedCreateReport.mockRejectedValueOnce(new Error("Unable to submit report."));
    render(<ReportAction target_type="CLUB" target_id="club-3"/>);
    fireEvent.click(screen.getByRole("button",{name:"Report Society"}));
    fireEvent.click(screen.getByRole("button",{name:"Submit report"}));
    await screen.findByText("Unable to submit report.");
    expect(screen.queryByText("Report submitted. An administrator will review it.")).toBeNull();
  });
});
