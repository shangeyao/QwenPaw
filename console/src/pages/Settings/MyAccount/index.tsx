import { useEffect, useMemo, useState } from "react";
import { Button, Card, Form, Input, Spin } from "antd";
import { useTranslation } from "react-i18next";
import { agentsApi } from "@/api/modules/agents";
import { authApi } from "@/api/modules/auth";
import { setAuthToken } from "@/api/config";
import { PageHeader } from "@/components/PageHeader";
import { useAppMessage } from "@/hooks/useAppMessage";
import { applyAuthSession, useAuthStore } from "@/stores/authStore";
import { getAgentDisplayName } from "@/utils/agentDisplayName";
import styles from "./index.module.less";

type MyAccountFormValues = {
  username: string;
  current_password: string;
  password?: string;
  confirmPassword?: string;
};

export default function MyAccountPage() {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const session = useAuthStore((state) => state.session);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [boundAgentLabel, setBoundAgentLabel] = useState("—");
  const [form] = Form.useForm<MyAccountFormValues>();

  const isAgentAccount = session?.role === "agent";

  const pageTitle = useMemo(
    () =>
      isAgentAccount ? t("account.myAccount") : t("account.myAccountAdmin"),
    [isAgentAccount, t],
  );

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const username = session?.username ?? "";
        form.setFieldsValue({
          username,
          current_password: "",
          password: undefined,
          confirmPassword: undefined,
        });

        if (isAgentAccount && session?.agentId) {
          const agentRes = await agentsApi.listAgents();
          const agent = agentRes.agents.find(
            (item) => item.id === session.agentId,
          );
          setBoundAgentLabel(
            agent
              ? `${getAgentDisplayName(agent, t)} (${agent.id})`
              : session.agentId,
          );
        }
      } catch (error) {
        console.error("Failed to load account page:", error);
        message.error(t("account.loadFailed"));
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [form, isAgentAccount, message, session, t]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (!values.password && values.username.trim() === session?.username) {
        message.warning(t("account.nothingToUpdate"));
        return;
      }

      setSaving(true);
      const response = await authApi.updateProfile(
        values.current_password,
        values.username.trim() !== session?.username
          ? values.username.trim()
          : undefined,
        values.password?.trim() || undefined,
      );

      setAuthToken(response.token);
      applyAuthSession({
        username: response.username || values.username.trim(),
        role: response.role ?? session?.role,
        agent_id: response.agent_id ?? session?.agentId,
      });

      form.setFieldsValue({
        username: response.username || values.username.trim(),
        current_password: "",
        password: undefined,
        confirmPassword: undefined,
      });
      message.success(t("account.updateSuccess"));
    } catch (error) {
      const detail = error instanceof Error ? error.message : "";
      message.error(detail || t("account.updateFailed"));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.centerState}>
          <Spin />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <PageHeader
        className={styles.pageHeader}
        parent={t("nav.settings")}
        current={pageTitle}
      />

      <Card>
        <p className={styles.description}>
          {t("account.myAccountDescription")}
        </p>

        {isAgentAccount && (
          <div className={styles.boundAgent}>
            <span className={styles.boundAgentLabel}>
              {t("account.boundAgent")}
            </span>
            <span>{boundAgentLabel}</span>
          </div>
        )}

        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="username"
            label={t("account.username")}
            rules={[{ required: true, message: t("account.usernameRequired") }]}
          >
            <Input placeholder={t("account.usernamePlaceholder")} />
          </Form.Item>

          <Form.Item
            name="current_password"
            label={t("account.currentPassword")}
            rules={[
              {
                required: true,
                message: t("account.currentPasswordRequired"),
              },
            ]}
          >
            <Input.Password />
          </Form.Item>

          <Form.Item name="password" label={t("account.newPassword")}>
            <Input.Password placeholder={t("account.newPasswordPlaceholder")} />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label={t("account.confirmPassword")}
            dependencies={["password"]}
            rules={[
              ({ getFieldValue }) => ({
                validator(_, value) {
                  const password = getFieldValue("password");
                  if (!password) {
                    return Promise.resolve();
                  }
                  if (!value) {
                    return Promise.reject(
                      new Error(t("account.confirmPasswordRequired")),
                    );
                  }
                  if (value === password) {
                    return Promise.resolve();
                  }
                  return Promise.reject(
                    new Error(t("account.passwordMismatch")),
                  );
                },
              }),
            ]}
          >
            <Input.Password
              placeholder={t("account.confirmPasswordPlaceholder")}
            />
          </Form.Item>

          <Button type="primary" htmlType="submit" loading={saving}>
            {t("account.save")}
          </Button>
        </Form>
      </Card>
    </div>
  );
}
