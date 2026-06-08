/**
 * A channel layer that only handles pure data serialization and parsing logic,
 * completely independent of the physical WebSocket network technology.
 *
 * This class is perfectly symmetrical to `python/core/channel.py` in the Python backend.
 */
export class Channel {
  /**
   * Injects network functions from the outside (FastAPIClient) via constructor (Dependency Injection).
   * This way, the word 'WebSocket' never appears in this file!
   *
   * @param sendMsgFunc Function to send a string out to the network
   * @param onReceiveRegister Function to register a callback that pushes received data into this channel
   * @param onMessageParsed Function to call to send the successfully parsed object to React
   */
  constructor(
    private sendMsgFunc: (text: string) => void,
    onReceiveRegister: (callback: (text: string) => void) => void,
    private onMessageParsed: (payload: any) => void
  ) {
    // Registers the receive pipeline (listener) upon creation. (Replaces Python's listen loop)
    onReceiveRegister((rawText: string) => {
      this.handleReceive(rawText)
    })
  }

  /**
   * Called when sending data from the frontend (React) to the Python server.
   * Performs JSON serialization and sends it out via the injected send function.
   */
  public send(payload: any): void {
    try {
      const jsonStr = JSON.stringify(payload)
      this.sendMsgFunc(jsonStr)
    } catch (error) {
      console.error('[Channel] Data serialization failed:', error)
    }
  }

  /**
   * Internal method called when text is received from the network.
   */
  private handleReceive(rawText: string): void {
    try {
      const payload = JSON.parse(rawText)

      // Passes the final parsed object to its destination (FastAPIClient).
      this.onMessageParsed(payload)
    } catch (error) {
      console.error('[Channel] Failed to parse received JSON:', rawText, error)
    }
  }
}
