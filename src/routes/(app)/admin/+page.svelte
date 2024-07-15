<script>
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';

	import {  getUsers } from '$lib/apis/users';

	import Pagination from '$lib/components/common/Pagination.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let users = [];

	let search = '';


	let page = 1;


	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		} else {
			users = await getUsers(localStorage.token);
		}
		loaded = true;
	});
	let sortKey = 'created_at'; // default sort key
	let sortOrder = 'asc'; // default sort order

	function setSortKey(key) {
		if (sortKey === key) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortOrder = 'asc';
		}
	}
</script>

{#if loaded}
	<div class="mt-0.5 mb-3 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('All Users')}
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
			<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{users.length}</span>
		</div>

		<div class="flex gap-1">
			<input
				class="w-full md:w-60 rounded-xl py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
				placeholder={$i18n.t('Search')}
				bind:value={search}
			/>
		</div>
	</div>

	<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
		<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full">
			<thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400">
				<tr>
					<th
						scope="col"
						class="px-3 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('role')}
					>
						{$i18n.t('Role')}
						{#if sortKey === 'role'}
							{sortOrder === 'asc' ? '▲' : '▼'}
						{:else}
							<span class="invisible">▲</span>
						{/if}
					</th>
					<th
						scope="col"
						class="px-3 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('name')}
					>
						{$i18n.t('Name')}
						{#if sortKey === 'name'}
							{sortOrder === 'asc' ? '▲' : '▼'}
						{:else}
							<span class="invisible">▲</span>
						{/if}
					</th>
					<th
						scope="col"
						class="px-3 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('email')}
					>
						{$i18n.t('Email')}
						{#if sortKey === 'email'}
							{sortOrder === 'asc' ? '▲' : '▼'}
						{:else}
							<span class="invisible">▲</span>
						{/if}
					</th>
					<th
						scope="col"
						class="px-3 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('oauth_sub')}
					>
						{$i18n.t('OAuth ID')}
						{#if sortKey === 'oauth_sub'}
							{sortOrder === 'asc' ? '▲' : '▼'}
						{:else}
							<span class="invisible">▲</span>
						{/if}
					</th>
					<th
						scope="col"
						class="px-3 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('last_active_at')}
					>
						{$i18n.t('Last Active')}
						{#if sortKey === 'last_active_at'}
							{sortOrder === 'asc' ? '▲' : '▼'}
						{:else}
							<span class="invisible">▲</span>
						{/if}
					</th>
					<th
						scope="col"
						class="px-3 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('created_at')}
					>
						{$i18n.t('Created at')}
						{#if sortKey === 'created_at'}
							{sortOrder === 'asc' ? '▲' : '▼'}
						{:else}
							<span class="invisible">▲</span>
						{/if}
					</th>

					<th scope="col" class="px-3 py-2 text-right" />
				</tr>
			</thead>
		</table>
	</div>

	<div class=" text-gray-500 text-xs mt-2 text-right">
		ⓘ {$i18n.t("Click on the user role button to change a user's role.")}
	</div>

	<Pagination bind:page count={users.length} />
{/if}

<style>
	.font-mona {
		font-family: 'Mona Sans';
	}

	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
