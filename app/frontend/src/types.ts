export interface Action {
  id: number;
  account_id: string;
  contact_id: string | null;
  action_type: string;
  title: string;
  description: string | null;
  priority: string;
  status: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}
