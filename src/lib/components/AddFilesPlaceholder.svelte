<script>
	import { getContext } from 'svelte';

	export let title = '';
	export let content = '';
	
</script>

<div class="px-3">
	<div class="text-center text-6xl mb-3">📄</div>
	<div class="text-center dark:text-white text-xl font-semibold z-50">
		{#if title}
			{title}
		{:else}
			{'Add Files'}
		{/if}
	</div>

	<slot
		><div class="px-2 mt-2 text-center text-sm dark:text-gray-200 w-full">
			{#if content}
				{content}
			{:else}
				{'Drop any files here to add to the conversation'}
			{/if}
		</div>
	</slot>
</div>
