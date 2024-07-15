<script>
	import { goto } from '$app/navigation';
	import { getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	let loaded = false;
	let mode = 'signin';

	let name = '';
	let email = '';
	let password = '';

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

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(error);
			return null;
		});

		await setSessionUser(sessionUser);
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
		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if loaded}
	<div class="fixed m-10 z-50">
		<div class="flex space-x-2">
			<div class=" self-center">
				<img
					crossorigin="anonymous"
					src="{WEBUI_BASE_URL}/static/favicon.png"
					class=" w-8 rounded-full"
					alt="logo"
				/>
			</div>
		</div>
	</div>

	<div class=" bg-white dark:bg-gray-950 min-h-screen w-full flex justify-center font-mona">

		<div class="w-full sm:max-w-md px-10 min-h-screen flex flex-col text-center">
			{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
				<div class=" my-auto pb-10 w-full">
					<div
						class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-medium dark:text-gray-200"
					>
						<div>
							{$i18n.t('Signing in')}
							{$i18n.t('to')}
							{$WEBUI_NAME}
						</div>

						<div>
							<Spinner />
						</div>
					</div>
				</div>
			{:else}
				<div class="  my-auto pb-10 w-full dark:text-gray-100">

					{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
						<div class="inline-flex items-center justify-center w-full">
							<hr class="w-64 h-px my-8 bg-gray-200 border-0 dark:bg-gray-700" />
						</div>
						<div class="flex flex-col space-y-2">
								<button
									class="flex items-center px-6 border-2 dark:border-gray-800 duration-300 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 w-full rounded-2xl dark:text-white text-sm py-3 transition"
									on:click={() => {
										window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
									}}
								>

									<span
										>{$i18n.t('Continue with {{provider}}', {
											provider: $config?.oauth?.providers?.oidc ?? 'SSO'
										})}</span
									>
								</button>
						</div>
					{/if}
				</div>
			{/if}
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
