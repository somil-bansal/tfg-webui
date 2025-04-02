<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { getSessionUser } from '$lib/apis/auths';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';

	let loaded = false;

	const querystringValue = (key: string) => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};

	const setSessionUser = async (sessionUser: any) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success(`You're now logged in.`);
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			if ($socket) {
				$socket.emit('user-join', { auth: { token: sessionUser.token } });
			}
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
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
			toast.error(`${error}`);
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo') as HTMLImageElement;

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = '/static/favicon-dark.png';

				darkImage.onload = () => {
					logo.src = '/static/favicon-dark.png';
					logo.style.filter = '';
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)';
				};
			}
		}
	}

	onMount(async () => {
		if ($user !== undefined) {
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
		await checkOauthCallback();
		loaded = true;
		setLogoImage();
	});
</script>

<svelte:head>
	<title>{$WEBUI_NAME}</title>
</svelte:head>

<div class="w-full h-screen max-h-[100dvh] text-white relative">
	<div class="w-full h-full absolute top-0 left-0 bg-white dark:bg-black"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div class="fixed m-10 z-50">
			<div class="flex space-x-2">
				<div class="self-center">
					<img
						id="logo"
						crossorigin="anonymous"
						src="{WEBUI_BASE_URL}/static/splash.png"
						class="w-6 rounded-full"
						alt="logo"
					/>
				</div>
			</div>
		</div>

		<div class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-50 text-black dark:text-white">
			<div class="w-full sm:max-w-md px-10 min-h-screen flex flex-col text-center">
				<div class="my-auto pb-10 w-full dark:text-gray-100">
					<div class="mb-1">
						<div class="text-2xl font-medium">
							Sign in to {$WEBUI_NAME}
						</div>
					</div>

					<div class="mt-5">
						<button
							class="flex justify-center items-center bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5"
							on:click={() => {
								window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-6 mr-3"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
								/>
							</svg>
							<span>Continue with Okta</span>
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
