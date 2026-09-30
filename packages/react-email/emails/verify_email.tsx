import { Text } from "@react-email/components"
import { LinkButton } from "../ui/Button"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"
import { Link } from "../ui/Link"

type VerifyEmailProps = {
  project_name: string
  username: string
  link: string
  valid_minutes: string
}

export default function VerifyEmail({
  project_name = "{{ project_name }}",
  username = "{{ username }}",
  link = "{{ link }}",
  valid_minutes = "{{ valid_minutes }}",
}: VerifyEmailProps) {
  return (
    <Layout
      title={project_name + " - Verify your email"}
      preview={"Verify your " + project_name + " email address"}
      project_name={project_name}
    >
      <Heading>Verify your email address</Heading>
      <Text style={bodyTextStyle}>Hi {username},</Text>
      <Text style={bodyTextStyle}>
        Confirm your email address to finish setting up your {project_name} account.
      </Text>
      <LinkButton href={link}>Verify email</LinkButton>
      <Text style={supportingTextStyle}>
        Or copy and paste this link into your browser:
        <br />
        <Link href={link}>{link}</Link>
      </Text>
      <Text style={supportingTextStyle}>
        This link will expire in {valid_minutes} minutes. If you did not create
        this account, you can safely ignore this email.
      </Text>
    </Layout>
  )
}

const bodyTextStyle = {
  color: "#334155",
  fontSize: "15px",
  lineHeight: "26px",
  margin: "0 0 18px",
}

const supportingTextStyle = {
  color: "#64748b",
  fontSize: "14px",
  lineHeight: "23px",
  margin: "0 0 16px",
}
