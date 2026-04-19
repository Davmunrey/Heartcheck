import { CreateOrganization } from "@clerk/nextjs";

export default function CreateOrganizationPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-8">
      <CreateOrganization afterCreateOrganizationUrl="/dashboard" />
    </div>
  );
}
