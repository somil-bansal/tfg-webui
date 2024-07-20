<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	import { user } from '$lib/stores';
	import { getContext, onMount } from 'svelte';

	import { fade } from 'svelte/transition';

	const i18n = getContext('i18n');


	let mounted = false;


	onMount(() => {
		mounted = true;
	});
</script>

{#key mounted}
	<div class="m-auto w-full max-w-6xl px-8 lg:px-24 pb-10">
		<div class="flex justify-start">
			<div class="flex -space-x-4 mb-1" in:fade={{ duration: 200 }}>
					<button>
						<img
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class=" size-[2.7rem] rounded-full border-[1px] border-gray-200 dark:border-none"
							alt="logo"
							draggable="false"
						/>
					</button>
			</div>
		</div>

		<div
			class=" mt-2 mb-4 text-3xl text-gray-800 dark:text-gray-100 font-semibold text-left flex items-center gap-4"
		>
			<div>
				<div class=" capitalize line-clamp-1" in:fade={{ duration: 200 }}>
						{$i18n.t('Hello, {{name}}', { name: $user.name })}
				</div>
				<div in:fade={{ duration: 200, delay: 200 }}>
						<div class=" font-medium text-gray-400 dark:text-gray-500 line-clamp-1">
							{$i18n.t('How can I assist?')}
						</div>
				</div>
			</div>
		</div>

<!--		<div class=" w-full" in:fade={{ duration: 200, delay: 300 }}>-->
<!--			<Suggestions-->
<!--				suggestionPrompts={models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??-->
<!--					$config.default_prompt_suggestions}-->
<!--				{submitPrompt}-->
<!--			/>-->
<!--		</div>-->
	</div>
{/key}
