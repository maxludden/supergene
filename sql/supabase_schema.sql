create extension if not exists pgcrypto;

create table if not exists public.books (
    id uuid primary key default gen_random_uuid(),
    source_fingerprint text not null unique,
    title text not null,
    creators text[] not null default '{}',
    language text,
    identifiers text[] not null default '{}',
    local_output_path text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.chapters (
    id uuid primary key default gen_random_uuid(),
    book_id uuid not null references public.books(id) on delete cascade,
    chapter_index integer not null,
    title text not null,
    toc_depth integer not null default 0,
    source_href text not null,
    markdown text not null,
    local_path text,
    asset_root text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (book_id, chapter_index)
);

create table if not exists public.conversion_warnings (
    id uuid primary key default gen_random_uuid(),
    book_id uuid not null references public.books(id) on delete cascade,
    code text not null,
    message text not null,
    source_href text,
    created_at timestamptz not null default now()
);

create index if not exists conversion_warnings_book_id_idx
    on public.conversion_warnings (book_id);

alter table public.books enable row level security;
alter table public.chapters enable row level security;
alter table public.conversion_warnings enable row level security;

do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'books'
          and policyname = 'service role manages books'
    ) then
        create policy "service role manages books"
            on public.books
            for all
            to service_role
            using (true)
            with check (true);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'chapters'
          and policyname = 'service role manages chapters'
    ) then
        create policy "service role manages chapters"
            on public.chapters
            for all
            to service_role
            using (true)
            with check (true);
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'conversion_warnings'
          and policyname = 'service role manages conversion warnings'
    ) then
        create policy "service role manages conversion warnings"
            on public.conversion_warnings
            for all
            to service_role
            using (true)
            with check (true);
    end if;
end $$;

grant usage on schema public to service_role;
grant select, insert, update, delete on public.books to service_role;
grant select, insert, update, delete on public.chapters to service_role;
grant select, insert, update, delete on public.conversion_warnings to service_role;

insert into storage.buckets (id, name, public)
values ('epub-assets', 'epub-assets', false)
on conflict (id) do update set public = excluded.public;

do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'storage'
          and tablename = 'objects'
          and policyname = 'service role manages epub assets'
    ) then
        create policy "service role manages epub assets"
            on storage.objects
            for all
            to service_role
            using (bucket_id = 'epub-assets')
            with check (bucket_id = 'epub-assets');
    end if;
end $$;

-- Uploads use paths like:
-- books/{book_id}/assets/images/pixel.png
--
-- If you intentionally expose these tables through the Data API for anon or
-- authenticated roles, add explicit grants and matching RLS policies first.
