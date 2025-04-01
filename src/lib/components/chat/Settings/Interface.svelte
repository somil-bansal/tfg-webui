<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { updateUserInfo } from '$lib/apis/users';
	import { getUserPosition } from '$lib/utils';
	const dispatch = createEventDispatcher();

	

	export let saveSettings: Function;

	let backgroundImageUrl = null;
	let inputFiles = null;
	let filesInputElement;

	// Addons
	let titleAutoGenerate = true;
	let autoTags = true;

	let responseAutoCopy = false;
	let widescreenMode = false;
	let splitLargeChunks = false;
	let scrollOnBranchChange = true;
	let userLocation = false;

	// Interface
	let defaultModelId = '';
	let showUsername = false;
	let notificationSound = true;

	let richTextInput = true;
	let promptAutocomplete = false;

	let largeTextAsFile = false;

	let landingPageMode = '';
	let chatBubble = true;
	let chatDirection: 'LTR' | 'RTL' = 'LTR';
	let ctrlEnterToSend = false;

	let collapseCodeBlocks = false;
	let expandDetails = false;

	let imageCompression = false;
	let imageCompressionSize = {
		width: '',
		height: ''
	};

	// Admin - Show Update Available Toast
	let showUpdateToast = true;
	let showChangelog = true;

	let hapticFeedback = false;

	let webSearch = null;

	const toggleExpandDetails = () => {
		expandDetails = !expandDetails;
		saveSettings({ expandDetails });
	};

	const toggleCollapseCodeBlocks = () => {
		collapseCodeBlocks = !collapseCodeBlocks;
		saveSettings({ collapseCodeBlocks });
	};

	const toggleSplitLargeChunks = async () => {
		splitLargeChunks = !splitLargeChunks;
		saveSettings({ splitLargeChunks: splitLargeChunks });
	};

	const togglePromptAutocomplete = async () => {
		promptAutocomplete = !promptAutocomplete;
		saveSettings({ promptAutocomplete: promptAutocomplete });
	};

	const togglesScrollOnBranchChange = async () => {
		scrollOnBranchChange = !scrollOnBranchChange;
		saveSettings({ scrollOnBranchChange: scrollOnBranchChange });
	};

	const toggleWidescreenMode = async () => {
		widescreenMode = !widescreenMode;
		saveSettings({ widescreenMode: widescreenMode });
	};

	const toggleChatBubble = async () => {
		chatBubble = !chatBubble;
		saveSettings({ chatBubble: chatBubble });
	};

	const toggleLandingPageMode = async () => {
		landingPageMode = landingPageMode === '' ? 'chat' : '';
		saveSettings({ landingPageMode: landingPageMode });
	};

	const toggleShowUpdateToast = async () => {
		showUpdateToast = !showUpdateToast;
		saveSettings({ showUpdateToast: showUpdateToast });
	};

	const toggleNotificationSound = async () => {
		notificationSound = !notificationSound;
		saveSettings({ notificationSound: notificationSound });
	};

	const toggleShowChangelog = async () => {
		showChangelog = !showChangelog;
		saveSettings({ showChangelog: showChangelog });
	};

	const toggleShowUsername = async () => {
		showUsername = !showUsername;
		saveSettings({ showUsername: showUsername });
	
	};

	const toggleImageCompression = async () => {
		imageCompression = !imageCompression;
		saveSettings({ imageCompression });
	};

	const toggleHapticFeedback = async () => {
		hapticFeedback = !hapticFeedback;
		saveSettings({ hapticFeedback: hapticFeedback });
	};


	const toggleTitleAutoGenerate = async () => {
		titleAutoGenerate = !titleAutoGenerate;
		saveSettings({
			title: {
				...$settings.title,
				auto: titleAutoGenerate
			}
		});
	};

	const toggleAutoTags = async () => {
		autoTags = !autoTags;
		saveSettings({ autoTags });
	};

	const toggleRichTextInput = async () => {
		richTextInput = !richTextInput;
		saveSettings({ richTextInput });
	};

	const toggleLargeTextAsFile = async () => {
		largeTextAsFile = !largeTextAsFile;
		saveSettings({ largeTextAsFile });
	};

	const toggleResponseAutoCopy = async () => {
		const permission = await navigator.clipboard
			.readText()
			.then(() => {
				return 'granted';
			})
			.catch(() => {
				return '';
			});

		console.log(permission);

		if (permission === 'granted') {
			responseAutoCopy = !responseAutoCopy;
			saveSettings({ responseAutoCopy: responseAutoCopy });
		} else {
			toast.error(
				'Clipboard write permission denied. Please check your browser settings to grant the necessary access.'
			);
		}
	};

	const toggleChangeChatDirection = async () => {
		chatDirection = chatDirection === 'LTR' ? 'RTL' : 'LTR';
		saveSettings({ chatDirection });
	};

	const togglectrlEnterToSend = async () => {
		ctrlEnterToSend = !ctrlEnterToSend;
		saveSettings({ ctrlEnterToSend });
	};

	const updateInterfaceHandler = async () => {
		saveSettings({
			models: [defaultModelId],
			imageCompressionSize: imageCompressionSize
		});
	};

	const toggleWebSearch = async () => {
		webSearch = webSearch === null ? 'always' : null;
		saveSettings({ webSearch: webSearch });
	};

	onMount(async () => {
		titleAutoGenerate = $settings?.title?.auto ?? true;
		autoTags = $settings.autoTags ?? true;

		responseAutoCopy = $settings.responseAutoCopy ?? false;

		showUsername = $settings.showUsername ?? false;
		showUpdateToast = $settings.showUpdateToast ?? true;
		showChangelog = $settings.showChangelog ?? true;


		richTextInput = $settings.richTextInput ?? true;
		promptAutocomplete = $settings.promptAutocomplete ?? false;
		largeTextAsFile = $settings.largeTextAsFile ?? false;

		collapseCodeBlocks = $settings.collapseCodeBlocks ?? false;
		expandDetails = $settings.expandDetails ?? false;

		landingPageMode = $settings.landingPageMode ?? '';
		chatBubble = $settings.chatBubble ?? true;
		widescreenMode = $settings.widescreenMode ?? false;
		splitLargeChunks = $settings.splitLargeChunks ?? false;
		scrollOnBranchChange = $settings.scrollOnBranchChange ?? true;
		chatDirection = $settings.chatDirection ?? 'LTR';
		userLocation = $settings.userLocation ?? false;

		notificationSound = $settings.notificationSound ?? true;

		hapticFeedback = $settings.hapticFeedback ?? false;
		ctrlEnterToSend = $settings.ctrlEnterToSend ?? false;

		imageCompression = $settings.imageCompression ?? false;
		imageCompressionSize = $settings.imageCompressionSize ?? { width: '', height: '' };

		defaultModelId = $settings?.models?.at(0) ?? '';
		if ($config?.default_models) {
			defaultModelId = $config.default_models.split(',')[0];
		}

		backgroundImageUrl = $settings.backgroundImageUrl ?? null;
		webSearch = $settings.webSearch ?? null;
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		updateInterfaceHandler();
		dispatch('save');
	}}
>
	<input
		bind:this={filesInputElement}
		bind:files={inputFiles}
		type="file"
		hidden
		accept="image/*"
		on:change={() => {
			let reader = new FileReader();
			reader.onload = (event) => {
				let originalImageUrl = `${event.target.result}`;

				backgroundImageUrl = originalImageUrl;
				saveSettings({ backgroundImageUrl });
			};

			if (
				inputFiles &&
				inputFiles.length > 0 &&
				['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(inputFiles[0]['type'])
			) {
				reader.readAsDataURL(inputFiles[0]);
			} else {
				console.log(`Unsupported File Type '${inputFiles[0]['type']}'.`);
				inputFiles = null;
			}
		}}
	/>

	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div>
			<div class=" mb-1.5 text-sm font-medium">{'UI'}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Landing Page Mode'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleLandingPageMode();
						}}
						type="button"
					>
						{#if landingPageMode === ''}
							<span class="ml-2 self-center">{'Default'}</span>
						{:else}
							<span class="ml-2 self-center">{'Chat'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Chat Bubble UI'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleChatBubble();
						}}
						type="button"
					>
						{#if chatBubble === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if !$settings.chatBubble}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs">
							{'Display the username instead of You in the Chat'}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleShowUsername();
							}}
							type="button"
						>
							{#if showUsername === true}
								<span class="ml-2 self-center">{'On'}</span>
							{:else}
								<span class="ml-2 self-center">{'Off'}</span>
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Widescreen Mode'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleWidescreenMode();
						}}
						type="button"
					>
						{#if widescreenMode === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Chat direction'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={toggleChangeChatDirection}
						type="button"
					>
						{#if chatDirection === 'LTR'}
							<span class="ml-2 self-center">{'LTR'}</span>
						{:else}
							<span class="ml-2 self-center">{'RTL'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{'Notification Sound'}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleNotificationSound();
						}}
						type="button"
					>
						{#if notificationSound === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if $user.role === 'admin'}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs">
							{'Toast notifications for new updates'}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleShowUpdateToast();
							}}
							type="button"
						>
							{#if showUpdateToast === true}
								<span class="ml-2 self-center">{'On'}</span>
							{:else}
								<span class="ml-2 self-center">{'Off'}</span>
							{/if}
						</button>
					</div>
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs">
							{'Show "What\'s New" modal on login'}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleShowChangelog();
							}}
							type="button"
						>
							{#if showChangelog === true}
								<span class="ml-2 self-center">{'On'}</span>
							{:else}
								<span class="ml-2 self-center">{'Off'}</span>
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<div class=" my-1.5 text-sm font-medium">{'Chat'}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Title Auto-Generation'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleTitleAutoGenerate();
						}}
						type="button"
					>
						{#if titleAutoGenerate === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Chat Tags Auto-Generation'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleAutoTags();
						}}
						type="button"
					>
						{#if autoTags === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{'Auto-Copy Response to Clipboard'}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleResponseAutoCopy();
						}}
						type="button"
					>
						{#if responseAutoCopy === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{'Rich Text Input for Chat'}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleRichTextInput();
						}}
						type="button"
					>
						{#if richTextInput === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if $config?.features?.enable_autocomplete_generation && richTextInput}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs">
							{'Prompt Autocompletion'}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								togglePromptAutocomplete();
							}}
							type="button"
						>
							{#if promptAutocomplete === true}
								<span class="ml-2 self-center">{'On'}</span>
							{:else}
								<span class="ml-2 self-center">{'Off'}</span>
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{'Paste Large Text as File'}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleLargeTextAsFile();
						}}
						type="button"
					>
						{#if largeTextAsFile === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Always Collapse Code Blocks'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleCollapseCodeBlocks();
						}}
						type="button"
					>
						{#if collapseCodeBlocks === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Always Expand Details'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleExpandDetails();
						}}
						type="button"
					>
						{#if expandDetails === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{'Chat Background Image'}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							if (backgroundImageUrl !== null) {
								backgroundImageUrl = null;
								saveSettings({ backgroundImageUrl });
							} else {
								filesInputElement.click();
							}
						}}
						type="button"
					>
						{#if backgroundImageUrl !== null}
							<span class="ml-2 self-center">{'Reset'}</span>
						{:else}
							<span class="ml-2 self-center">{'Upload'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Allow User Location'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleUserLocation();
						}}
						type="button"
					>
						{#if userLocation === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Haptic Feedback'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleHapticFeedback();
						}}
						type="button"
					>
						{#if hapticFeedback === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>


			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{'Enter Key Behavior'}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							togglectrlEnterToSend();
						}}
						type="button"
					>
						{#if ctrlEnterToSend === true}
							<span class="ml-2 self-center">{'Ctrl+Enter to Send'}</span>
						{:else}
							<span class="ml-2 self-center">{'Enter to Send'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{'Scroll to bottom when switching between branches'}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							togglesScrollOnBranchChange();
						}}
						type="button"
					>
						{#if scrollOnBranchChange === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Web Search in Chat'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleWebSearch();
						}}
						type="button"
					>
						{#if webSearch === 'always'}
							<span class="ml-2 self-center">{'Always'}</span>
						{:else}
							<span class="ml-2 self-center">{'Default'}</span>
						{/if}
					</button>
				</div>
			</div>


			<div class=" my-1.5 text-sm font-medium">{'File'}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{'Image Compression'}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleImageCompression();
						}}
						type="button"
					>
						{#if imageCompression === true}
							<span class="ml-2 self-center">{'On'}</span>
						{:else}
							<span class="ml-2 self-center">{'Off'}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if imageCompression}
				<div>
					<div class=" py-0.5 flex w-full justify-between text-xs">
						<div class=" self-center text-xs">{'Image Max Compression Size'}</div>

						<div>
							<input
								bind:value={imageCompressionSize.width}
								type="number"
								class="w-20 bg-transparent outline-hidden text-center"
								min="0"
								placeholder="Width"
							/>x
							<input
								bind:value={imageCompressionSize.height}
								type="number"
								class="w-20 bg-transparent outline-hidden text-center"
								min="0"
								placeholder="Height"
							/>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<div class="flex justify-end text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{'Save'}
		</button>
	</div>
</form>
