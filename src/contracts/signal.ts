/**
 * The most basic top-level signal (event) interface for communication
 * (e.g., WebSocket) between the frontend (Electron) and backend (Python).
 */
export interface BaseSignal {
  /**
   * Unique name of the signal (routing identifier).
   * Must match the python object name.
   */
  type: string

  /**
   * Fires this signal object to the backend.
   */
  emit(): void
}

/**
 * Signal Factory function for the frontend.
 * Eliminates repetitive boilerplate code and creates a signal with perfect type inference in a single line.
 *
 * @param type Class name of the signal to be received by the Python backend (e.g., "SendMessageSignal")
 * @returns A generator function that takes a payload and returns a signal object equipped with an emit() method
 */
export function defineSignal<Payload = void>(type: string) {
  // Accepts arguments based on the generic Payload type.
  // If it's a void type (no data), it can optionally be left empty.
  return (payload?: Payload) => {
    const signal = {
      // 1. The factory secretly injects the type at runtime.
      type,

      // 2. Merges the data (Payload) provided by the developer. (Ignored if no data)
      ...(payload || {}),

      // 3. Mounts the emit button.
      emit: function () {
        // Cast to any to prevent TypeScript errors, then call Preload API
        const api = (window as any).api
        if (api && api.sendSignal) {
          api.sendSignal(this)
        } else {
          // Console output for debugging before Preload is connected
          console.warn(
            `[Emit Fired] ${type}: But window.api.sendSignal is not connected yet.`,
            this
          )
        }
      }
    }

    // Finally, makes it recognized as an object combining HOSignalBase and the Payload type provided by the developer.
    return signal as BaseSignal & Payload
  }
}

/**
 * [Usage Example Guide]
 *
 * 1. Define a signal with data
 * export const SendMessageSignal = defineSignal<{ text: string }>("SendMessageSignal");
 *
 * 2. Define a signal without data (Trigger)
 * export const StopGenerationSignal = defineSignal<void>("StopGenerationSignal");
 *
 * 3. When firing (Can be used immediately in any component)
 * SendMessageSignal({ text: "Hello" }).emit();
 * StopGenerationSignal().emit();
 */
