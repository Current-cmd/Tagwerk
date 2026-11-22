import { Composition } from "remotion";
import { TagwerkDemo, TOTAL_FRAMES } from "./Video";

export const RemotionRoot: React.FC = () => (
  <Composition id="TagwerkDemo" component={TagwerkDemo} durationInFrames={TOTAL_FRAMES} fps={30} width={1920} height={1080} />
);
