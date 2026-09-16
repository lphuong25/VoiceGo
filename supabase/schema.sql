-- Run this in Supabase SQL Editor.
-- Supabase Auth manages the users table.

create table if not exists public.saved_data (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    transcription text not null,
    translation text,
    vocabulary_list jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

alter table public.saved_data enable row level security;

drop policy if exists "Users can read their own saved data" on public.saved_data;
create policy "Users can read their own saved data"
on public.saved_data for select
using (auth.uid() = user_id);

drop policy if exists "Users can insert their own saved data" on public.saved_data;
create policy "Users can insert their own saved data"
on public.saved_data for insert
with check (auth.uid() = user_id);
