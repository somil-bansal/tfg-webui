<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Message from './Message.svelte';

	

	export let messages = [];
</script>

<div class="py-3 space-y-3">
	{#each messages as message, idx}
		<Message
			{message}
			{idx}
			onDelete={() => {
				messages = messages.filter((message, messageIdx) => messageIdx !== idx);
			}}
		/>
	{/each}
</div>
