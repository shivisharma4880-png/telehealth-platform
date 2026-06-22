import { redirect } from "next/navigation";

/** Legacy route from the removed in-browser video consult; patient visits use audio consult or home. */
export default function PatientConsultLegacyRedirect() {
  redirect("/patient/home");
}
