import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Table,
  Tag,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { PlusOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { accountApi } from "@/api/modules/account";
import { agentsApi } from "@/api/modules/agents";
import type { WebAccountSummary } from "@/api/types/account";
import type { AgentSummary } from "@/api/types/agents";
import { PageHeader } from "@/components/PageHeader";
import { useAppMessage } from "@/hooks/useAppMessage";
import { getAgentDisplayName } from "@/utils/agentDisplayName";
import styles from "./index.module.less";

type AccountFormValues = {
  username: string;
  password?: string;
  confirmPassword?: string;
  agent_id?: string;
  current_password?: string;
};

export default function AccountsPage() {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<WebAccountSummary[]>([]);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingAccount, setEditingAccount] =
    useState<WebAccountSummary | null>(null);
  const [form] = Form.useForm<AccountFormValues>();

  const agentNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const agent of agents) {
      map.set(agent.id, getAgentDisplayName(agent, t));
    }
    return map;
  }, [agents, t]);

  const agentAccountById = useMemo(() => {
    const map = new Map<string, string>();
    for (const account of accounts) {
      if (account.role === "agent" && account.agent_id) {
        map.set(account.agent_id, account.username);
      }
    }
    return map;
  }, [accounts]);

  const agentSelectOptions = useMemo(() => {
    return agents.map((agent) => {
      const boundUsername = agentAccountById.get(agent.id);
      const occupiedByOther =
        boundUsername !== undefined &&
        boundUsername !== editingAccount?.username;
      const label = `${getAgentDisplayName(agent, t)} (${agent.id})`;
      return {
        value: agent.id,
        label: occupiedByOther
          ? `${label} — ${t("account.agentHasAccount", {
              username: boundUsername,
            })}`
          : label,
        disabled: occupiedByOther,
      };
    });
  }, [agents, agentAccountById, editingAccount, t]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [accountRes, agentRes] = await Promise.all([
        accountApi.listAccounts(),
        agentsApi.listAgents(),
      ]);
      setAccounts(accountRes.accounts);
      setAgents(agentRes.agents);
    } catch (error) {
      console.error("Failed to load accounts:", error);
      message.error(t("account.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [message, t]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const openCreateModal = () => {
    setEditingAccount(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEditModal = (account: WebAccountSummary) => {
    setEditingAccount(account);
    form.setFieldsValue({
      username: account.username,
      agent_id: account.agent_id ?? undefined,
      password: undefined,
      confirmPassword: undefined,
      current_password: undefined,
    });
    setModalOpen(true);
  };

  const handleDelete = async (account: WebAccountSummary) => {
    try {
      await accountApi.deleteAccount(account.username);
      message.success(t("account.deleteSuccess"));
      await fetchData();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "";
      message.error(detail || t("account.deleteFailed"));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      if (editingAccount) {
        if (editingAccount.role === "admin") {
          await accountApi.updateAccount(editingAccount.username, {
            new_username: values.username?.trim() || undefined,
            password: values.password?.trim() || undefined,
            current_password: values.current_password,
          });
        } else {
          await accountApi.updateAccount(editingAccount.username, {
            new_username: values.username?.trim() || undefined,
            password: values.password?.trim() || undefined,
            agent_id: values.agent_id,
          });
        }
        message.success(t("account.updateSuccess"));
      } else {
        await accountApi.createAccount({
          username: values.username.trim(),
          password: values.password!.trim(),
          role: "agent",
          agent_id: values.agent_id,
        });
        message.success(t("account.createSuccess"));
      }

      setModalOpen(false);
      await fetchData();
    } catch (error) {
      if (error instanceof Error && error.message) {
        message.error(error.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const columns: ColumnsType<WebAccountSummary> = [
    {
      title: t("account.username"),
      dataIndex: "username",
      key: "username",
    },
    {
      title: t("account.role"),
      dataIndex: "role",
      key: "role",
      render: (role: WebAccountSummary["role"]) => (
        <Tag color={role === "admin" ? "gold" : "blue"}>
          {role === "admin" ? t("account.roleAdmin") : t("account.roleAgent")}
        </Tag>
      ),
    },
    {
      title: t("account.boundAgent"),
      dataIndex: "agent_id",
      key: "agent_id",
      render: (agentId: string | null | undefined) =>
        agentId ? `${agentNameById.get(agentId) ?? agentId} (${agentId})` : "—",
    },
    {
      title: t("common.actions"),
      key: "actions",
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => openEditModal(record)}>
            {t("common.edit")}
          </Button>
          {record.role === "agent" && (
            <Popconfirm
              title={t("account.deleteConfirm")}
              onConfirm={() => handleDelete(record)}
            >
              <Button type="link" danger>
                {t("common.delete")}
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

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
        current={t("account.title")}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={openCreateModal}
          >
            {t("account.createAgentAccount")}
          </Button>
        }
      />

      <Table
        rowKey="username"
        columns={columns}
        dataSource={accounts}
        pagination={false}
      />

      <Modal
        title={
          editingAccount
            ? t("account.editTitle", { username: editingAccount.username })
            : t("account.createAgentAccount")
        }
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={saving}
        okText={t("common.save")}
        cancelText={t("common.cancel")}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="username"
            label={t("account.username")}
            rules={[{ required: true, message: t("account.usernameRequired") }]}
          >
            <Input placeholder={t("account.usernamePlaceholder")} />
          </Form.Item>

          {!editingAccount && (
            <Form.Item
              name="agent_id"
              label={t("account.boundAgent")}
              rules={[{ required: true, message: t("account.agentRequired") }]}
            >
              <Select
                placeholder={t("account.agentPlaceholder")}
                options={agentSelectOptions}
              />
            </Form.Item>
          )}

          {editingAccount?.role === "agent" && (
            <Form.Item name="agent_id" label={t("account.boundAgent")}>
              <Select
                placeholder={t("account.agentPlaceholder")}
                options={agentSelectOptions}
              />
            </Form.Item>
          )}

          {editingAccount?.role === "admin" && (
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
          )}

          <Form.Item
            name="password"
            label={
              editingAccount ? t("account.newPassword") : t("account.password")
            }
            rules={
              editingAccount
                ? []
                : [{ required: true, message: t("account.passwordRequired") }]
            }
          >
            <Input.Password
              placeholder={
                editingAccount
                  ? t("account.newPasswordPlaceholder")
                  : t("account.passwordPlaceholder")
              }
            />
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
        </Form>
      </Modal>
    </div>
  );
}
