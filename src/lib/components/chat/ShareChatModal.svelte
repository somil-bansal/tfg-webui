<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';

	export let chatId;

	let chat = null;
	let shareUrl = null;
	const i18n = getContext('i18n');

	const shareLocalChat = async () => {
		const _chat = chat;

		const sharedChat = await shareChatById(localStorage.token, chatId);
		shareUrl = `${window.location.origin}/s/${sharedChat.id}`;
		console.log(shareUrl);
		chat = await getChatById(localStorage.token, chatId);

		return shareUrl;
	};

	const shareChat = async () => {
		const _chat = chat.chat;
		console.log('share', _chat);

		toast.success($i18n.t('Redirecting you to The Finance Genie'));
		const url = 'http://localhost:8080.com';
		// const url = 'http://localhost:5173';

		const tab = await window.open(`${url}/chats/upload`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(
						JSON.stringify({
							chat: _chat,
							models: $models.filter((m) => _chat.models.includes(m.id))
						}),
						'*'
					);
				}
			},
			false
		);
	};

	export let show = false;

	const isDifferentChat = (_chat) => {
		if (!chat) {
			return true;
		}
		if (!_chat) {
			return false;
		}
		return chat.id !== _chat.id || chat.share_id !== _chat.share_id;
	};

	$: if (show) {
		(async () => {
			if (chatId) {
				const _chat = await getChatById(localStorage.token, chatId);
				if (isDifferentChat(_chat)) {
					chat = _chat;
				}
			} else {
				chat = null;
				console.log(chat);
			}
		})();
	}
</script>

<Modal bind:show size="md">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class=" text-lg font-medium self-center">{$i18n.t('Share Chat')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		{#if chat}
			<div class="px-5 pt-4 pb-5 w-full flex flex-col justify-center">
				<div class=" text-sm dark:text-gray-300 mb-1">
					{#if chat.share_id}
						<a href="/s/{chat.share_id}" target="_blank"
							>{$i18n.t('You have shared this chat')}
							<span class=" underline">{$i18n.t('before')}</span>.</a
						>
						{$i18n.t('Click here to')}
						<button
							class="underline"
							on:click={async () => {
								const res = await deleteSharedChatById(localStorage.token, chatId);

								if (res) {
									chat = await getChatById(localStorage.token, chatId);
								}
							}}
							>{$i18n.t('delete this link')}
						</button>
						{$i18n.t('and create a new shared link.')}
					{:else}
						{$i18n.t(
							"Messages you send after creating your link won't be shared. Users with the URL will be able to view the shared chat."
						)}
					{/if}
				</div>
			</div>
		{/if}
	</div>
</Modal>
