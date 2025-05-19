<script lang="ts">
	import DOMPurify from 'dompurify';

	import { getVersionUpdates, getWebhookUrl, updateWebhookUrl } from '$lib/apis';
	import {
		getAdminConfig,
		updateAdminConfig,
	} from '$lib/apis/auths';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	let adminConfig = null;
	let webhookUrl = '';

	const updateHandler = async () => {
		webhookUrl = await updateWebhookUrl(localStorage.token, webhookUrl);
		const res = await updateAdminConfig(localStorage.token, adminConfig);
		if (res) {
			saveHandler();
		} else {
			toast.error(i18n.t('Failed to update settings'));
		}
	};

</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class="mt-0.5 space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		{#if adminConfig !== null}
			<div class="">
				<div class="mb-3.5">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="mb-2.5">
						<div class=" mb-1 text-xs font-medium flex space-x-2 items-center">
							<div>
								{$i18n.t('Version')}
							</div>
						</div>
					</div>

				<div class="mb-3">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('Authentication')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Default User Role')}</div>
						<div class="flex items-center relative">
							<select
								class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
								bind:value={adminConfig.DEFAULT_USER_ROLE}
								placeholder="Select a role"
							>
								<option value="pending">{$i18n.t('pending')}</option>
								<option value="user">{$i18n.t('user')}</option>
								<option value="admin">{$i18n.t('admin')}</option>
							</select>
						</div>
					</div>


					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Show Admin Details in Account Pending Overlay')}
						</div>

						<Switch bind:state={adminConfig.SHOW_ADMIN_DETAILS} />
					</div>

					<div class="mb-2.5 flex w-full justify-between pr-2">
						<div class=" self-center text-xs font-medium">{$i18n.t('Enable API Key')}</div>

						<Switch bind:state={adminConfig.ENABLE_API_KEY} />
					</div>

					{#if adminConfig?.ENABLE_API_KEY}
						<div class="mb-2.5 flex w-full justify-between pr-2">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('API Key Endpoint Restrictions')}
							</div>

							<Switch bind:state={adminConfig.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS} />
						</div>

						{#if adminConfig?.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS}
							<div class=" flex w-full flex-col pr-2">
								<div class=" text-xs font-medium">
									{$i18n.t('Allowed Endpoints')}
								</div>

								<input
									class="w-full mt-1 rounded-lg text-sm dark:text-gray-300 bg-transparent outline-hidden"
									type="text"
									placeholder={`e.g.) /api/v1/messages, /api/v1/channels`}
									bind:value={adminConfig.API_KEY_ALLOWED_ENDPOINTS}
								/>

							</div>
						{/if}
					{/if}

					<div class=" mb-2.5 w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('JWT Expiration')}</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								placeholder={`e.g.) "30m","1h", "10d". `}
								bind:value={adminConfig.JWT_EXPIRES_IN}
							/>
						</div>

						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Valid time units:')}
							<span class=" text-gray-300 font-medium"
								>{$i18n.t("'s', 'm', 'h', 'd', 'w' or '-1' for no expiration.")}</span
							>
						</div>
					</div>


					</div>
				</div>

				<div class="mb-3">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('Features')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />


					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">{$i18n.t('Enable Message Rating')}</div>

						<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Notes')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_NOTES} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Channels')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_CHANNELS} />
					</div>

					<div class="mb-2.5 flex w-full items-center justify-between pr-2">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('User Webhooks')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
					</div>

					<div class="mb-2.5 w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('WebUI URL')}</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								placeholder={`e.g.) "http://localhost:3000"`}
								bind:value={adminConfig.WEBUI_URL}
							/>
						</div>

						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t(
								'Enter the public URL of your WebUI. This URL will be used to generate links in the notifications.'
							)}
						</div>
					</div>

					<div class=" w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Webhook URL')}</div>
						</div>

						<div class="flex mt-2 space-x-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								placeholder={`https://example.com/webhook`}
								bind:value={webhookUrl}
							/>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
