<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let src = '';
	export let alt = '';

	export let className = ' w-full outline-hidden focus:outline-hidden';
	export let imageClassName = 'rounded-lg';

	export let dismissible = false;
	export let onDismiss = () => {};

	let _src = '';
	$: _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;

</script>


<div class=" relative group w-fit">

	{#if dismissible}
		<div class=" absolute -top-1 -right-1">
			<button
				class=" bg-white text-black border border-white rounded-full group-hover:visible invisible transition"
				type="button"
				on:click={() => {
					onDismiss();
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-4"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
	{/if}
</div>
