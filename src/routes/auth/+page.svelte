<script>
	import { goto } from '$app/navigation';
	import { getSessionUser } from '$lib/apis/auths';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { config, socket, user, WEBUI_NAME } from '$lib/stores';
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	let loaded = false;

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			goto('/');
		}
	};


	const checkOauthCallback = async () => {
		if (!$page.url.hash) {
			return;
		}
		const hash = $page.url.hash.substring(1);
		if (!hash) {
			return;
		}
		const params = new URLSearchParams(hash);
		const token = params.get('token');
		if (!token) {
			return;
		}
		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(error);
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	onMount(async () => {
		if ($user !== undefined) {
			await goto('/');
		}
		await checkOauthCallback();
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if loaded}
	<div class="bg-white dark:bg-gray-950 min-h-screen w-full flex justify-center font-mona">
		<div class="w-full sm:max-w-md min-h-screen flex flex-col text-center">
			<div class="my-auto pb-10 w-full dark:text-gray-100">
				<div class="flex flex-col items-center space-y-6">
					<div class="self-center">
						<img
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class="w-60 rounded-full"
							alt="logo"
						/>
					</div>
					<div class="self-center text-5xl font-bold dark:text-gray-100">
						The Finance Genie
					</div>
					<div class="self-center text-3xl font-bold dark:text-gray100">
						TFG Gen AI
					</div>
					<div class="flex flex-col font-bold">
						<button
							class="flex items-center px-6 border-2 dark:border-gray-800 duration-300 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 w-full rounded-2xl dark:text-white text-sm py-3 transition"
							on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
									}}
						>
                        <span>
                            {$i18n.t('Continue to sign in {{provider}}', {
															provider: $config?.oauth?.providers?.oidc ?? 'SSO'
														})}
                        </span>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>

{/if}

<style>
    .font-mona {
        font-family: 'Mona Sans', -apple-system, 'Arimo', ui-sans-serif, system-ui, 'Segoe UI', Roboto,
        Ubuntu, Cantarell, 'Noto Sans', sans-serif, 'Helvetica Neue', Arial, 'Apple Color Emoji',
        'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
    }
</style>
