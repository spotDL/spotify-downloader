// Thin wrapper over the Control Room ui primitive, preserving the legacy
// `Button` API (variant subset + default `type="button"`) so existing call
// sites keep compiling unchanged.
import { Button as UIButton, type ButtonProps as UIButtonProps } from "./ui/button";

export type ButtonProps = UIButtonProps;

export function Button({ type = "button", ...props }: ButtonProps) {
  return <UIButton type={type} {...props} />;
}
